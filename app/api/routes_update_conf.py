from flask import request, jsonify
from functools import wraps
from . import api_blueprint

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.logger import app_logger as logger
from lib.query_data import ScalingConfigManager
from lib.aws_db import AWSDBManager
from lib.aws_eks import EKSManager
from lib.k8s_client import K8sClient
from core.core import get_highest_instance_config
from conf import settings



@api_blueprint.route('/upgrade/<int:capacity>', methods=['PUT'])
def upgrade_level(capacity):
    '''
    升级到指定的人数容量级别
    前提是DB已经升级到指定配置

    1.配置比升级预估低，通知升级，不升级
    2.配置比升级预估高或者相等，通知信息，升级

    '''
    scaling_manager = ScalingConfigManager()

    aws_db_manager = AWSDBManager(
        access_key_id=settings.AWS_ACCESS_KEY_ID,
        secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )
    aws_eks_manager = EKSManager(
        settings.AWS_REGION, 
        settings.AWS_ACCESS_KEY_ID, 
        settings.AWS_SECRET_ACCESS_KEY, 
        settings.EKS_CLUSTER_NAME
    )
    k8s_client = K8sClient(
        kube_config_path=settings.KUBE_FILE_PATH,
        context_name=settings.CLUSTER_CONTEXT
    )

    complete_config = scaling_manager.get_complete_config(capacity)

    # 如果是 600 级别 代表降级到平常级别
    if capacity == 600:
        # hpa 还是需要更新
        scaling_res = []
        for namespace, services in complete_config["services"].items():
            for service_name, service_config in services.items():
                # 更新HPA最小副本数
                if service_config["hpa_name"]:
                    try:
                        hpa_name = service_config["hpa_name"]
                        replicas = service_config["replicas"]
                        
                        # 调用K8s客户端更新HPA
                        k8s_client.update_hpa_scaling(
                            namespace=namespace,
                            hpa_name=hpa_name,
                            min_replicas=replicas
                        )
                        
                        scaling_res.append(
                            f"successful:{namespace}/{hpa_name}->hpa_min:{replicas}"
                        )
                        logger.info(f"已将 {namespace}/{hpa_name} 最小副本数更新为 {replicas}")
                    except Exception as e:
                        error_msg = f"failure:{namespace}/{hpa_name}->hpa_min:{str(e)}"
                        scaling_res.append(error_msg)
                        logger.error(error_msg)
                
                # 删除节点亲和性
                if service_config["pool_name"]:
                    try:
                        # 调用K8s客户端删除节点亲和性
                        # 更新节点组最小值
                        state = aws_eks_manager.update_nodegroup_scaling(service_config["pool_name"],0,20,0)
                        if  service_config["pool_name"]:
                            k8s_client.remove_node_affinity(
                                deployment_name=service_name,
                                namespace=namespace
                            )
                            scaling_res.append(
                                f"successful:{namespace}/{service_name}->node_affinity_remove:{service_config['pool_name']}-->node_pool_upgrade:{state}"
                            )
                            logger.info(f"已将 {namespace}/{service_name} 节点亲和性删除{service_config['pool_name']}-->node_pool_upgrade:{state}")
                    except Exception as e:
                        error_msg = f"failure:{namespace}/{service_name}->node_affinity_remove:{str(e)}-->node_pool_upgrade:{state}"
                        scaling_res.append(error_msg)
                        logger.error(error_msg)

        # 返回结果
        return jsonify({"upgrade_capacity":capacity,"k8s_res":scaling_res}), 200 

    # 下面是升级到600以上的级别
    # 根据数据库中的级别，找到对应的 hpa 和 node_affinity
    # 比对数据库配置
    rds_instance_type = aws_db_manager.get_rds_cluster_instance_type(settings.RDS_CLUSTER_NAME)
    if not rds_instance_type:
        logger.error(f"获取RDS实例类型失败: {settings.RDS_CLUSTER_NAME}")
    # 获取最高配置的RDS节点类型
    _, rds_highest_type = get_highest_instance_config(rds_instance_type)

    # 获取当前Redis实例类型
    redis_type = aws_db_manager.get_elasticache_redis_node_type(settings.REDIS_OSS_NAME)
    if not redis_type:
        logger.error(f"获取Redis实例类型失败: {settings.REDIS_OSS_NAME}")

    # 获取目标实例类型
    target_db_type = complete_config["postgres"]['instance_type']
    target_redis_type = complete_config["redis"]['instance_type']

    # 当前配置级别容量人数
    current_db_level = scaling_manager.get_user_capacity_by_postgres_instance_type(rds_highest_type)
    current_redis_level = scaling_manager.get_user_capacity_by_redis_instance_type(redis_type)

    # 目标配置级别容量人数
    target_db_level = complete_config["postgres"]['level']
    target_redis_level = complete_config["redis"]['level']

    is_ready = False
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
            "type": rds_highest_type,
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

    if not is_ready:
        # 返回需要升级的信息
        return jsonify({"upgrade_capacity":capacity,"state":is_ready,"db_conf":{"rds":db_status,"redis":redis_status}}), 200
    
    # 更新hpa 和 节点亲和性
    scaling_results = []

    # 更新节点组最小值
    nodegroups = aws_eks_manager.list_nodegroups()
    node_info = {}
    for nodegroup_name in nodegroups:
        desired_size = aws_eks_manager.get_nodegroup_desired_size(nodegroup_name)
        node_info[nodegroup_name] = desired_size
    for pool in node_info:
        if node_info[pool] == 0:
            up_pool_state = aws_eks_manager.update_nodegroup_scaling(pool,0,20,1)
            if up_pool_state:
                scaling_results.append(
                    f"eks_pool:{pool},is_upgrade:{up_pool_state}"
                )
            logger.error(f"eks_pool:{pool},is_upgrade:{up_pool_state}")


    # 遍历所有服务并进行更新
    for namespace, services in complete_config["services"].items():
        for service_name, service_config in services.items():
            # 更新HPA最小副本数
            if service_config["hpa_name"]:
                try:
                    hpa_name = service_config["hpa_name"]
                    replicas = service_config["replicas"]
                    
                    # 调用K8s客户端更新HPA
                    k8s_client.update_hpa_scaling(
                        namespace=namespace,
                        hpa_name=hpa_name,
                        min_replicas=replicas
                    )
                    
                    scaling_results.append(
                        f"successful:{namespace}/{hpa_name}->hpa_min:{replicas}"
                    )
                    logger.info(f"已将 {namespace}/{hpa_name} 最小副本数更新为 {replicas}")
                except Exception as e:
                    error_msg = f"failure:{namespace}/{hpa_name}->hpa_min:{str(e)}"
                    scaling_results.append(error_msg)
                    logger.error(error_msg)
            
            # 更新节点亲和性
            if service_config["pool_name"]:
                try:
                    # 调用K8s客户端更新节点亲和性
                    if  service_config["pool_name"]:
                        k8s_client.set_nodegroup_affinity(
                            namespace=namespace,
                            deployment_name=service_name,
                            nodegroup_key="eks.amazonaws.com/nodegroup",
                            nodegroup_values=service_config["pool_name"]
                        )
                        scaling_results.append(
                            f"successful:{namespace}/{service_name}-->node_affinity:{service_config['pool_name']}"
                        )
                        logger.info(f"已将 {namespace}/{service_name} 节点亲和性更新为 {service_config['pool_name']}")
                except Exception as e:
                    error_msg = f"failure:{namespace}/{service_name}->node_affinity:{str(e)}"
                    scaling_results.append(error_msg)
                    logger.error(error_msg)

    return jsonify({"upgrade_capacity":capacity,"state":is_ready,"db_conf":{"rds":db_status,"redis":redis_status},"k8s_res":scaling_results}), 200
