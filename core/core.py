import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.logger import app_logger as logger
from lib.get_analytics_user import get_active_users
from lib.get_analytics_user import get_mock_users
from lib.query_data import ScalingConfigManager
from lib.feishu_bot import FeishuRichTextBot
from lib.aws_db import AWSDBManager
from lib.aws_eks import EKSManager
from lib.k8s_client import K8sClient
from conf import settings


class AutoScalingService:
    def __init__(self):
        """初始化自动伸缩服务"""
        self.scaling_manager = ScalingConfigManager()
        self.feishu_bot = FeishuRichTextBot(
            webhook_url=settings.FEISHU_WEBHOOK_URL,
            max_retries=5,
            retry_delay=1
        )
        self.aws_db_manager = AWSDBManager(
            access_key_id=settings.AWS_ACCESS_KEY_ID,
            secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.k8s_client = K8sClient(
            kube_config_path=settings.KUBE_FILE_PATH,
            context_name=settings.CLUSTER_CONTEXT
        )
        self.aws_eks_manager = EKSManager(
            settings.AWS_REGION, 
            settings.AWS_ACCESS_KEY_ID, 
            settings.AWS_SECRET_ACCESS_KEY, 
            settings.EKS_CLUSTER_NAME
        )

        # 记录上次扩容事件
        self.last_scaling_time = None
        self.last_level = None
        
        logger.info("自动伸缩服务已初始化")
    
    def get_current_capacity_level(self):
        """
        根据线上的DB配置以及HPA最小配置 获取到当前配置级别
        """
        try:
            # 获取DB 配置类型
            rds_instance_types = self.aws_db_manager.get_rds_cluster_instance_type(settings.RDS_CLUSTER_NAME)
            if rds_instance_types:
                rds_highest_id, rds_highest_type = get_highest_instance_config(rds_instance_types)
                logger.info(f"最高配置实例: {rds_highest_id}: {rds_highest_type}")
            else:
                logger.error(f"RDS集群 {settings.RDS_CLUSTER_NAME} 实例类型查询失败")

            # 获取Redis类型
            redis_node_type = self.aws_db_manager.get_elasticache_redis_node_type(settings.REDIS_OSS_NAME)
            if redis_node_type:
                logger.info(f"Redis实例 {settings.REDIS_OSS_NAME} 当前节点类型: {redis_node_type}")
            else:
                logger.error(f"Redis实例 {settings.REDIS_OSS_NAME} 节点类型查询失败")

            # 直接通过 istio的replic rds redis 获取当前级别
            # 当前istio-ingress hpa min
            istio_ingress_hpa = self.k8s_client.get_hpa_scaling_config(
                hpa_name=settings.HPA_NAME,
                namespace=settings.HPA_NAMESPACE
            )
            istio_ingress_hpa_min = istio_ingress_hpa['min_replicas']

            # 比对配置 返回当前数据库中记录的 level 
            capacity_level = self.scaling_manager.determine_capacity_level(
                hpa_name=settings.HPA_NAME, 
                namespace=settings.HPA_NAMESPACE, 
                service_name=settings.HPA_SERVICE_NAME,
                redis_instance_type=redis_node_type, 
                postgres_instance_type=rds_highest_type,
                replicas=istio_ingress_hpa_min
            )
            return capacity_level.user_capacity

        except Exception as e:
            logger.error(f"获取当前容量级别时发生错误: {str(e)}")
            return 0

    def check_and_scale(self):
        """检查用户数量并执行伸缩操作"""
        try:
            # 获取当前活跃用户数
            user_count = get_active_users(settings.KEY_FILE_LOCATION, settings.PROPERTY_ID)
            # user_count = get_mock_users(api_url="http://10.4.59.123:5000/api/online-users")
            # user_count = 1000
            
            # 判断是否需要扩容及获取目标级别
            scaling_required, target_level, current_capacity = self._evaluate_scaling_need(user_count)
            if not scaling_required:
                return
            
            # 获取完整配置
            complete_config = self.scaling_manager.get_complete_config(user_count)
            
            # 检查基础设施是否满足要求
            infrastructure_ready, db_status, redis_status = self._check_infrastructure(complete_config)
            
            # 准备并发送通知
            self._send_scaling_notification(
                user_count, current_capacity, target_level.user_capacity, 
                infrastructure_ready, db_status, redis_status, complete_config
            )
            
            # 如果基础设施已准备好，执行K8s资源伸缩
            if infrastructure_ready:
                # 判断节点组情况，如果期望值为0 需要修改，如果不为0 不用处理，直接升级
                nodegroups = self.aws_eks_manager.list_nodegroups()
                node_info = {}
                for nodegroup_name in nodegroups:
                    desired_size = self.aws_eks_manager.get_nodegroup_desired_size(nodegroup_name)
                    node_info[nodegroup_name] = desired_size
                for pool in node_info:
                    if node_info[pool] == 0:
                        up_pool_state = self.aws_eks_manager.update_nodegroup_scaling(pool,0,20,1)

                scaling_results = self._scale_kubernetes_resources(complete_config)
                if scaling_results:
                    scaling_message = []
                    for res in scaling_results:
                        scaling_message.append(
                            [
                                {"tag": "text", "text": str(res)},
                            ]
                        )
                self.feishu_bot.send_rich_text(
                    title = f"⚠️ 资源伸缩信息",
                    content = scaling_message
                )
                self._update_scaling_history(target_level.user_capacity)
                
        except Exception as e:
            error_message = [
                [
                    {"tag": "text", "text": "错误信息"},
                    {"tag": "text", "text": {str(e)}},
                ]
            ]
            logger.error(error_message, exc_info=True)
            # 发送错误通知
            self.feishu_bot.send_rich_text(
                title="❌ 自动伸缩服务异常",
                content=error_message
            )

    def _evaluate_scaling_need(self, user_count):
        """评估是否需要进行扩容"""
        # 获取目标容量级别
        target_level = self.scaling_manager.get_target_level(user_count)
        if not target_level:
            logger.error("无法确定目标容量级别")
            return False, None, None
        
        level_user_capacity = target_level.user_capacity

        logger.info(f"目标容量级别: {level_user_capacity}")
        
        # 获取当前系统配置的容量级别
        current_capacity = self.get_current_capacity_level()
        

        # 如果用户数低于600 不需要操作
        if user_count < 600:
            # 还是需要检查当前配置是否高于600，高于600 还是需要降配
            if current_capacity > 600:
                logger.info(f"用户数低于600，但当前配置容量级别为{current_capacity}，需要降配")
                
                # 发送降级通知但不执行操作
                message_content = [
                    [                
                        {"tag": "text", "text": "时间: "},
                        {"tag": "text", "text": datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
                    ],
                    [
                        {"tag": "text", "text": "👥 当前活跃用户数: "},
                        {"tag": "text", "text": str(user_count)},
                    ],
                    [
                        {"tag": "text", "text": "⚙️ 当前系统配置容纳级别: "},
                        {"tag": "text", "text": str(current_capacity)},
                    ],
                    [
                        {"tag": "text", "text": "⚙️ 需要调整目标配置容纳级别: "},
                        {"tag": "text", "text": str(level_user_capacity)},
                    ],
                    [
                        {"tag": "text", "text": "根据配置，需上线手动调整降配"},
                    ]
                ]
                self.feishu_bot.send_rich_text(
                    title = f"⚠️ 降配通知 - 用户数低于600",
                    content = message_content
                )
            else:
                logger.info("用户数低于600，当前配置适合，不需要操作")

            return False, None, None
        
        # 检查是否需要降级 - 如果目标容量小于当前容量，只发送通知不执行操作
        is_downgrade = level_user_capacity < current_capacity
        if is_downgrade:
            logger.info(f"检测到降级请求（当前:{current_capacity} -> 目标:{level_user_capacity}），仅发送通知不执行操作")
            
            # 发送降级通知但不执行操作
            message_content = [
                [                
                    {"tag": "text", "text": "时间: "},
                    {"tag": "text", "text": datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
                ],
                [
                    {"tag": "text", "text": "👥 当前活跃用户数: "},
                    {"tag": "text", "text": str(user_count)},
                ],
                [
                    {"tag": "text", "text": "⚙️ 当前系统配置容纳级别: "},
                    {"tag": "text", "text": str(current_capacity)},
                ],
                [
                    {"tag": "text", "text": "⚙️ 需要调整目标配置容纳级别: "},
                    {"tag": "text", "text": str(level_user_capacity)},
                ],
                [
                    {"tag": "text", "text": "根据配置，需上线手动调整降配"},
                ]
            ]
            self.feishu_bot.send_rich_text(
                title = f"⚠️ 降配通知",
                content = message_content
            )
            return False, None, None
        
        # 如果目标级别与当前级别相同，不执行操作
        if level_user_capacity == current_capacity:
            logger.info(f"目标容量级别与当前配置相同 ({level_user_capacity})，无需操作")
            return False, None, None
        
        # 检查是否与上次扩容级别相同且时间间隔小于10分钟
        current_time = datetime.now()
        if (self.last_scaling_time and self.last_level == level_user_capacity and 
            (current_time - self.last_scaling_time).seconds < 600):
            logger.info(f"最近已执行过级别 {level_user_capacity} 的扩容，跳过")
            return False, None, None
        
        return True, target_level, current_capacity

    def _check_infrastructure(self, complete_config):
        """
        检查数据库和Redis配置是否满足目标配置，仅比较实例类型 
        如果目标配置比当前配置大的多也是可以升级
        capacity_level 比对
        """
        try:
            # 获取当前RDS实例类型
            rds_instance_type = self.aws_db_manager.get_rds_cluster_instance_type(settings.RDS_CLUSTER_NAME)
            if not rds_instance_type:
                logger.error(f"获取RDS实例类型失败: {settings.RDS_CLUSTER_NAME}")
                return False, None, None
            

            # 获取最高配置的RDS节点类型
            _, highest_rds_type = get_highest_instance_config(rds_instance_type)

            # 获取当前Redis实例类型
            redis_type = self.aws_db_manager.get_elasticache_redis_node_type(settings.REDIS_OSS_NAME)
            if not redis_type:
                logger.error(f"获取Redis实例类型失败: {settings.REDIS_OSS_NAME}")
                return False, None, None
            
            # 获取目标实例类型
            target_db_type = complete_config["postgres"]['instance_type']
            target_redis_type = complete_config["redis"]['instance_type']
            
            # 不能简单的判断当前配置相等，需要判断 当前配置容量人数比目标配置小(需要通知升级数据库)。当前配置容量人数比目标配置大，当前配置容量人数和目标配置相等 （返回True 不用通知升级）
            is_ready = False
            # 当前配置级别容量人数
            current_db_level = self.scaling_manager.get_user_capacity_by_postgres_instance_type(highest_rds_type)
            current_redis_level = self.scaling_manager.get_user_capacity_by_redis_instance_type(redis_type)

            # 目标配置级别容量人数
            target_db_level = complete_config["postgres"]['level']
            target_redis_level = complete_config["redis"]['level']

            # 基于容量人数判断是否满足要求
            db_meets_capacity = False
            redis_meets_capacity = False

            # 判断数据库容量是否满足要求
            if current_db_level is not None and target_db_level is not None:
                db_meets_capacity = current_db_level >= target_db_level
                logger.info(f"数据库容量比较: 当前容量 {current_db_level} {'≥' if db_meets_capacity else '<'} 目标容量 {target_db_level}")
            else:
                logger.warning(f"无法比较数据库容量: 当前容量 {current_db_level}, 目标容量 {target_db_level}")

            # 判断Redis容量是否满足要求
            if current_redis_level is not None and target_redis_level is not None:
                redis_meets_capacity = current_redis_level >= target_redis_level
                logger.info(f"Redis容量比较: 当前容量 {current_redis_level} {'≥' if redis_meets_capacity else '<'} 目标容量 {target_redis_level}")
            else:
                logger.warning(f"无法比较Redis容量: 当前容量 {current_redis_level}, 目标容量 {target_redis_level}")

            # 构建返回状态信息
            db_status = {
                "current": {
                    "type": highest_rds_type,
                    "capacity": current_db_level
                },
                "target": {
                    "type": target_db_type,
                    "capacity": target_db_level
                },
                "meets_capacity": db_meets_capacity
            }

            redis_status = {
                "current": {
                    "type": redis_type,
                    "capacity": current_redis_level
                },
                "target": {
                    "type": target_redis_type,
                    "capacity": target_redis_level
                },
                "meets_capacity": redis_meets_capacity
            }

            # 只有当两者都满足容量要求时，才返回True
            is_ready = db_meets_capacity and redis_meets_capacity
            # is_ready = True

            # 返回整体满足状态和各组件状态
            return is_ready, db_status, redis_status

            
        except Exception as e:
            logger.error(f"检查基础设施时发生错误: {str(e)}")
            return False, None, None

    def _scale_kubernetes_resources(self, complete_config):
        """执行Kubernetes资源的伸缩操作"""
        scaling_results = []
        
        # 遍历所有服务并进行更新
        for namespace, services in complete_config["services"].items():
            for service_name, service_config in services.items():
                # 更新HPA最小副本数
                if service_config["hpa_name"]:
                    try:
                        hpa_name = service_config["hpa_name"]
                        replicas = service_config["replicas"]
                        
                        # 调用K8s客户端更新HPA
                        self.k8s_client.update_hpa_scaling(
                            namespace=namespace,
                            hpa_name=hpa_name,
                            min_replicas=replicas
                        )
                        
                        scaling_results.append(
                            f"- ✅ 已将 {namespace}/{hpa_name} 最小副本数更新为 {replicas}"
                        )
                        logger.info(f"已将 {namespace}/{hpa_name} 最小副本数更新为 {replicas}")
                    except Exception as e:
                        error_msg = f"- ❌ 更新 {namespace}/{hpa_name} 失败: {str(e)}"
                        scaling_results.append(error_msg)
                        logger.error(error_msg)
                
                # 更新节点亲和性
                if service_config["pool_name"]:
                    try:
                        # 调用K8s客户端更新节点亲和性
                        if  service_config["pool_name"]:
                            self.k8s_client.set_nodegroup_affinity(
                                namespace=namespace,
                                deployment_name=service_name,
                                nodegroup_key="eks.amazonaws.com/nodegroup",
                                nodegroup_values=service_config["pool_name"]
                            )
                            scaling_results.append(
                                f"- ✅ 已将 {namespace}/{service_name} 节点亲和性更新为 {service_config['pool_name']}"
                            )
                            logger.info(f"已将 {namespace}/{service_name} 节点亲和性更新为 {service_config['pool_name']}")
                    except Exception as e:
                        error_msg = f"- ❌ 更新 {namespace}/{service_name} 节点亲和性失败: {str(e)}"
                        scaling_results.append(error_msg)
                        logger.error(error_msg)
        
        return scaling_results

    def _send_scaling_notification(self, user_count, current_capacity, target_capacity, 
                                infrastructure_ready, db_status, redis_status, complete_config):
        """发送扩容通知，使用飞书富文本格式"""
        message_title = f"🚨 [生产环境] 系统资源通知"
        
        # 构建符合飞书富文本格式的消息内容
        message_content = [
            # 检查时间
            [
                {"tag": "text", "text": "时间: "},
                {"tag": "text", "text": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            ],
            # 当前用户数
            [
                {"tag": "text", "text": "👥 当前活跃用户数: "},
                {"tag": "text", "text": str(user_count)}
            ],
            # 当前配置级别
            [
                {"tag": "text", "text": "⚙️ 当前系统配置容纳级别: "},
                {"tag": "text", "text": str(current_capacity)}
            ],
            # 目标配置级别
            [
                {"tag": "text", "text": "⚙️ 需要调整目标配置容纳级别: "},
                {"tag": "text", "text": str(target_capacity)}
            ]
        ]
        
        if infrastructure_ready:
            # 添加基础设施就绪信息
            message_content.append([
                {"tag": "text", "text": "🔧 基础设施状态: "},
                {"tag": "text", "text": "✅ 数据库和Redis配置已满足要求"}
            ])
            message_content.append([
                {"tag": "text", "text": "RDS当前配置: "},
                {"tag": "text", "text": str(db_status['current']['type'])}
            ])
            message_content.append([
                {"tag": "text", "text": "Redis当前配置: "},
                {"tag": "text", "text": str(redis_status['current']['type'])}
            ])
        
            # K8s扩容信息占位符
            message_content.append([
                {"tag": "text", "text": "🔄 K8s资源HPA扩容将被执行"}
            ])
        else:
            # 添加基础设施不满足要求的信息
            message_content.append([
                {"tag": "text", "text": "🔧 基础设施状态: "},
                {"tag": "text", "text": "❌ DB资源类型不满足要求"}
            ])
            message_content.append([])
            # 添加PostgreSQL配置差异
            if not db_status["meets_capacity"]:
                message_content.append([
                    {"tag": "text", "text": "📌 资源升级建议："},
                ])
                message_content.append([
                    {"tag": "text", "text": "🗄️ PostgreSQL 数据库"}
                ])
                message_content.append([
                    {"tag": "text", "text": "当前配置: "},
                    {"tag": "text", "text": str(db_status['current']['type'])}
                ])
                message_content.append([
                    {"tag": "text", "text": "需要配置: "},
                    {"tag": "text", "text": str(db_status['target']['type'])}
                ])
            message_content.append([])
            # 添加Redis配置差异
            if not redis_status["meets_capacity"]:
                message_content.append([
                    {"tag": "text", "text": "🧠 Redis 缓存"}
                ])
                message_content.append([
                    {"tag": "text", "text": "当前配置: "},
                    {"tag": "text", "text": str(redis_status['current']['type'])}
                ])
                message_content.append([
                    {"tag": "text", "text": "需要配置: "},
                    {"tag": "text", "text": str(redis_status['target']['type'])}
                ])
            
            # 添加操作建议
            message_content.append([
                {"tag": "text", "text": "⚠️ 请运维人员尽快升级数据库和缓存资源!"}
            ])
        
        # 发送通知
        self.feishu_bot.send_rich_text(
            title=message_title,
            content=message_content
        )
        logger.info(f"已发送扩容通知: {message_title}")

    def _update_scaling_history(self, target_capacity):
        """更新扩容历史记录"""
        self.last_scaling_time = datetime.now()
        self.last_level = target_capacity

def get_highest_instance_config(instance_types):
    """
    获取实例列表中配置最高的实例
    
    Args:
        instance_types (dict): 包含实例ID和实例类型的字典 {instance_id: instance_type}
        
    Returns:
        tuple: (highest_instance_id, highest_instance_type) 配置最高的实例ID和类型
    """
    if not instance_types:
        return None, None
        
    highest_id = None
    highest_type = None
    max_value = -1
    
    for instance_id, instance_type in instance_types.items():
        # logger.info(f"实例 {instance_id}: {instance_type}")
        size = instance_type.split('.')[-1]  # 获取最后一部分，如large, xlarge, 8xlarge
        
        # 计算实例大小的数值
        if size == "large":
            value = 1
        elif size == "xlarge":
            value = 2
        elif "xlarge" in size:
            # 处理如2xlarge, 4xlarge等情况
            value = int(size.replace("xlarge", "") or "0") + 2
        else:
            # 处理其他可能的情况
            value = 0
            
        if value > max_value:
            max_value = value
            highest_id = instance_id
            highest_type = instance_type
            
    return highest_id, highest_type

if __name__ == "__main__":
    auto_scaling = AutoScalingService()
    level = auto_scaling.get_current_capacity_level()
    print(f"当前级别:{level}")

    # auto_scaling.check_and_scale()