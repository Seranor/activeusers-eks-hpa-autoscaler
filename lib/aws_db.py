import boto3
from botocore.exceptions import ClientError

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.logger import app_logger as logger


class AWSDBManager:
    """AWS数据库管理类，用于管理RDS和ElastiCache Redis实例"""
    
    def __init__(self, region_name, access_key_id, secret_access_key):
        """
        初始化AWS数据库管理器
        
        Args:
            region_name (str): AWS区域名称
            access_key_id (str): AWS访问密钥ID
            secret_access_key (str): AWS私有访问密钥
        """
        self.region_name = region_name
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        
        # 初始化AWS客户端
        self.rds_client = boto3.client(
            'rds',
            region_name=self.region_name,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key
        )
        
        self.elasticache_client = boto3.client(
            'elasticache',
            region_name=self.region_name,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key
        )
    
    def get_rds_cluster_instance_type(self, cluster_name):
        """
        查询RDS集群的实例类型信息
        
        Args:
            cluster_name (str): RDS集群名称
            
        Returns:
            dict: 包含实例ID和对应实例类型的字典，失败则返回空字典
        """
        try:
            # 获取集群实例信息
            response = self.rds_client.describe_db_clusters(DBClusterIdentifier=cluster_name)
            if not response['DBClusters']:
                logger.error(f"aws db -- 未找到RDS集群: {cluster_name}")
                return {}
                
            db_cluster = response['DBClusters'][0]
            db_instance_identifiers = [member['DBInstanceIdentifier'] for member in db_cluster['DBClusterMembers']]
            
            instance_types = {}
            for instance_id in db_instance_identifiers:
                instance_info = self.rds_client.describe_db_instances(DBInstanceIdentifier=instance_id)
                instance_class = instance_info['DBInstances'][0]['DBInstanceClass']
                instance_types[instance_id] = instance_class
                
            return instance_types
            
        except ClientError as e:
            logger.error(f"aws db -- 查询RDS集群实例类型时出错: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"aws db -- 发生未预期的错误: {str(e)}")
            return {}
    
    def upgrade_rds_cluster_instance_type(self, cluster_name, new_instance_type):
        """
        升级RDS集群的实例类型
        
        Args:
            cluster_name (str): RDS集群名称
            new_instance_type (str): 新的实例类型，例如'db.r5.large'
        
        Returns:
            bool: 升级操作是否成功发起
        """
        try:
            # 获取集群实例信息
            response = self.rds_client.describe_db_clusters(DBClusterIdentifier=cluster_name)
            if not response['DBClusters']:
                logger.error(f"aws db -- 未找到RDS集群: {cluster_name}")
                return False
    
            db_cluster = response['DBClusters'][0]
            db_instances = db_cluster['DBClusterMembers']
    
            if not db_instances:
                logger.error(f"aws db -- 集群 {cluster_name} 中未找到实例")
                return False
    
            # 对集群中的每个实例发起升级操作
            for db_instance in db_instances:
                instance_id = db_instance['DBInstanceIdentifier']
                logger.info(f"aws db -- 正在升级RDS实例 {instance_id} 至 {new_instance_type}")
    
                # 修改实例类型
                self.rds_client.modify_db_instance(
                    DBInstanceIdentifier=instance_id,
                    DBInstanceClass=new_instance_type,
                    ApplyImmediately=True
                )
    
                logger.info(f"aws db -- 已成功发起实例 {instance_id} 的升级操作，新实例类型: {new_instance_type}")
    
            logger.info(f"aws db -- 已成功发起RDS集群 {cluster_name} 中所有实例的升级操作，新实例类型: {new_instance_type}")
            return True
    
        except ClientError as e:
            logger.error(f"aws db -- 升级RDS集群时出错: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"aws db -- 发生未预期的错误: {str(e)}")
            return False
    
    def get_elasticache_redis_node_type(self, redis_name):
        """
        查询ElastiCache Redis实例的节点类型
        
        Args:
            redis_name (str): ElastiCache Redis复制组或单节点实例名称
            
        Returns:
            str: Redis实例的节点类型，查询失败则返回空字符串
        """
        try:
            # 检查是否为复制组
            try:
                response = self.elasticache_client.describe_replication_groups(
                    ReplicationGroupId=redis_name
                )
                
                if len(response['ReplicationGroups']) > 0:
                    node_type = response['ReplicationGroups'][0]['CacheNodeType']
                    # logger.info(f"aws db -- Redis复制组 {redis_name} 的节点类型为: {node_type}")
                    return node_type
            except ClientError:
                # 不是复制组，继续尝试作为单节点缓存集群查询
                pass
                
            # 尝试作为单节点缓存集群查询
            try:
                response = self.elasticache_client.describe_cache_clusters(
                    CacheClusterId=redis_name
                )
                node_type = response['CacheClusters'][0]['CacheNodeType']
                # logger.info(f"aws db -- Redis实例 {redis_name} 的节点类型为: {node_type}")
                return node_type
            except ClientError as e:
                logger.error(f"aws db -- 找不到Redis实例或复制组: {redis_name}. 错误: {str(e)}")
                return ""
                
        except Exception as e:
            logger.error(f"aws db -- 发生未预期的错误: {str(e)}")
            return ""
    
    def upgrade_elasticache_redis_node_type(self, redis_name, new_node_type):
        """
        升级非集群模式的ElastiCache Redis实例的节点类型
        
        Args:
            redis_name (str): ElastiCache Redis复制组或单节点实例名称
            new_node_type (str): 新的节点类型，例如'cache.m5.large'
        
        Returns:
            bool: 升级操作是否成功发起
        """
        try:
            # 检查是否为复制组
            try:
                response = self.elasticache_client.describe_replication_groups(
                    ReplicationGroupId=redis_name
                )
                
                if len(response['ReplicationGroups']) > 0:
                    is_replication_group = True
                    # logger.info(f"aws db -- 检测到 {redis_name} 是非集群模式的Redis复制组")
                else:
                    is_replication_group = False
            except ClientError:
                # 不是复制组，尝试作为单节点缓存集群查询
                try:
                    response = self.elasticache_client.describe_cache_clusters(
                        CacheClusterId=redis_name
                    )
                    is_replication_group = False
                    # logger.info(f"aws db -- 检测到 {redis_name} 是单节点Redis实例")
                except ClientError as e:
                    logger.error(f"aws db -- 找不到Redis实例或复制组: {redis_name}. 错误: {str(e)}")
                    return False
    
            logger.info(f"aws db -- 开始升级非集群模式Redis '{redis_name}' 的节点类型至 {new_node_type}")
    
            if is_replication_group:
                # 修改非集群模式的复制组
                self.elasticache_client.modify_replication_group(
                    ReplicationGroupId=redis_name,
                    CacheNodeType=new_node_type,
                    ApplyImmediately=True
                )
                logger.info(f"aws db -- 已成功发起Redis复制组 {redis_name} 的升级操作，新节点类型: {new_node_type}")
            else:
                # 修改单节点缓存集群
                self.elasticache_client.modify_cache_cluster(
                    CacheClusterId=redis_name,
                    CacheNodeType=new_node_type,
                    ApplyImmediately=True
                )
                logger.info(f"aws db -- 已成功发起Redis实例 {redis_name} 的升级操作，新节点类型: {new_node_type}")
    
            logger.info(f"aws db -- 非集群模式Redis '{redis_name}' 的升级操作已成功发起，变更过程将在后台完成")
            return True
    
        except ClientError as e:
            logger.error(f"aws db -- 升级Redis实例时出错: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"aws db -- 发生未预期的错误: {str(e)}")
            return False


if __name__ == '__main__':
    from conf import settings
    
    # 创建AWS数据库管理器实例
    db_manager = AWSDBManager(
        region_name=settings.AWS_REGION,
        access_key_id=settings.AWS_ACCESS_KEY_ID,
        secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
    
    # 查询RDS集群实例类型
    rds_instance_types = db_manager.get_rds_cluster_instance_type(settings.RDS_CLUSTER_NAME)
    if rds_instance_types:
        highest_id = None
        highest_type = None
        max_value = -1
        for instance_id, instance_type in rds_instance_types.items():
            logger.info(f"实例 {instance_id}: {instance_type}")
            size = instance_type.split('.')[-1]  # 获取最后一部分，如large, xlarge, 8xlarge
            if size == "large":
                value = 1
            elif size == "xlarge":
                value = 2
            elif "xlarge" in size:
                value = int(size.replace("xlarge", "") or "0") + 2
            if value > max_value:
                max_value = value
                highest_id = instance_id
                highest_type = instance_type
        logger.info(f"最高配置实例: {highest_id}: {highest_type}")
    else:
        logger.error(f"RDS集群 {settings.RDS_CLUSTER_NAME} 实例类型查询失败")
    
    # 查询Redis实例类型
    redis_node_type = db_manager.get_elasticache_redis_node_type(settings.REDIS_OSS_NAME)
    if redis_node_type:
        logger.info(f"Redis实例 {settings.REDIS_OSS_NAME} 当前节点类型: {redis_node_type}")
    else:
        logger.error(f"Redis实例 {settings.REDIS_OSS_NAME} 节点类型查询失败")
    
    # # 升级RDS集群实例类型
    # success = db_manager.upgrade_rds_cluster_instance_type(
    #     cluster_name=settings.RDS_CLUSTER_NAME,
    #     new_instance_type='db.r7g.xlarge'  # db.r7g.large
    # )
    
    # if success:
    #     logger.info("RDS集群实例类型升级操作已成功发起")
    # else:
    #     logger.error("RDS集群实例类型升级操作发起失败")
    
    # # 升级非集群模式的ElastiCache Redis实例类型
    # success = db_manager.upgrade_elasticache_redis_node_type(
    #     redis_name=settings.REDIS_OSS_NAME,
    #     new_node_type='cache.c7gn.xlarge'  # cache.m6g.large    cache.t3.small
    # )
    
    # if success:
    #     logger.info("Redis实例类型升级操作已成功发起")
    # else:
    #     logger.error("Redis实例类型升级操作发起失败")
