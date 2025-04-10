import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import peewee as pw
from playhouse.shortcuts import model_to_dict
from lib.models import db,ServiceConfig,RedisConfig,PostgresConfig,CapacityLevel
from lib.logger import app_logger as logger


class CapacityConfigManager:
    """容量配置管理接口，提供对容量配置相关模型的增删改查功能"""
    
    def __init__(self):
        """初始化数据库连接并确保表存在"""
        try:
            db.connect(reuse_if_open=True)
            db.create_tables([CapacityLevel, ServiceConfig, RedisConfig, PostgresConfig], safe=True)
            logger.info("数据库连接成功并确保表存在")
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise
    
    def __del__(self):
        """关闭数据库连接"""
        if not db.is_closed():
            db.close()
    
    # ============= CapacityLevel 操作 =============
    def create_capacity_level(self, user_capacity):
        """创建新的容量级别"""
        try:
            with db.atomic():
                level = CapacityLevel.create(user_capacity=user_capacity)
                logger.info(f"创建容量级别成功: {level}")
                return level
        except pw.IntegrityError:
            logger.error(f"容量级别 {user_capacity} 已存在")
            return None
        except Exception as e:
            logger.error(f"创建容量级别失败: {str(e)}")
            return None
    
    def get_capacity_level(self, user_capacity=None, id=None):
        """获取容量级别，可按用户容量或ID查询"""
        try:
            if user_capacity is not None:
                return CapacityLevel.get_or_none(CapacityLevel.user_capacity == user_capacity)
            elif id is not None:
                return CapacityLevel.get_or_none(CapacityLevel.id == id)
            else:
                return list(CapacityLevel.select().order_by(CapacityLevel.user_capacity))
        except Exception as e:
            logger.error(f"查询容量级别失败: {str(e)}")
            return None
    
    def update_capacity_level(self, id, user_capacity):
        """更新容量级别"""
        try:
            with db.atomic():
                level = CapacityLevel.get_or_none(CapacityLevel.id == id)
                if not level:
                    logger.error(f"未找到ID为 {id} 的容量级别")
                    return False
                
                level.user_capacity = user_capacity
                level.save()
                logger.info(f"更新容量级别成功: {level}")
                return True
        except pw.IntegrityError:
            logger.error(f"容量级别 {user_capacity} 已存在")
            return False
        except Exception as e:
            logger.error(f"更新容量级别失败: {str(e)}")
            return False
    
    def delete_capacity_level(self, id):
        """删除容量级别"""
        try:
            with db.atomic():
                level = CapacityLevel.get_or_none(CapacityLevel.id == id)
                if not level:
                    logger.error(f"未找到ID为 {id} 的容量级别")
                    return False
                
                level.delete_instance(recursive=True)  # 级联删除关联的配置
                logger.info(f"删除容量级别成功: ID={id}")
                return True
        except Exception as e:
            logger.error(f"删除容量级别失败: {str(e)}")
            return False
    
    # ============= ServiceConfig 操作 =============
    def create_service_config(self, capacity_level_id, service_name, namespace, replicas, 
                              hpa_name=None, pool_name=None):
        """创建服务配置"""
        try:
            with db.atomic():
                level = CapacityLevel.get_or_none(CapacityLevel.id == capacity_level_id)
                if not level:
                    logger.error(f"未找到ID为 {capacity_level_id} 的容量级别")
                    return None
                
                service = ServiceConfig.create(
                    capacity_level=level,
                    service_name=service_name,
                    namespace=namespace,
                    replicas=replicas,
                    hpa_name=hpa_name,
                    pool_name=pool_name
                )
                logger.info(f"创建服务配置成功: {service}")
                return service
        except pw.IntegrityError:
            logger.error(f"服务配置已存在: {capacity_level_id}, {service_name}, {namespace}")
            return None
        except Exception as e:
            logger.error(f"创建服务配置失败: {str(e)}")
            return None
    
    def get_service_config(self, capacity_level_id=None, id=None):
        """获取服务配置"""
        try:
            if id is not None:
                return ServiceConfig.get_or_none(ServiceConfig.id == id)
            elif capacity_level_id is not None:
                return list(ServiceConfig.select().where(
                    ServiceConfig.capacity_level == capacity_level_id
                ))
            else:
                return list(ServiceConfig.select())
        except Exception as e:
            logger.error(f"查询服务配置失败: {str(e)}")
            return None
    
    def update_service_config(self, id, replicas=None, hpa_name=None, pool_name=None):
        """更新服务配置"""
        try:
            with db.atomic():
                service = ServiceConfig.get_or_none(ServiceConfig.id == id)
                if not service:
                    logger.error(f"未找到ID为 {id} 的服务配置")
                    return False
                
                if replicas is not None:
                    service.replicas = replicas
                if hpa_name is not None:
                    service.hpa_name = hpa_name
                if pool_name is not None:
                    service.pool_name = pool_name
                
                service.save()
                logger.info(f"更新服务配置成功: {service}")
                return True
        except Exception as e:
            logger.error(f"更新服务配置失败: {str(e)}")
            return False
    
    def delete_service_config(self, id):
        """删除服务配置"""
        try:
            with db.atomic():
                service = ServiceConfig.get_or_none(ServiceConfig.id == id)
                if not service:
                    logger.error(f"未找到ID为 {id} 的服务配置")
                    return False
                
                service.delete_instance()
                logger.info(f"删除服务配置成功: ID={id}")
                return True
        except Exception as e:
            logger.error(f"删除服务配置失败: {str(e)}")
            return False
    
    # ============= RedisConfig 操作 =============
    def create_redis_config(self, capacity_level_id, instance_type=None, memory_gb=None, bandwidth_gb=None):
        """创建Redis配置"""
        try:
            with db.atomic():
                level = CapacityLevel.get_or_none(CapacityLevel.id == capacity_level_id)
                if not level:
                    logger.error(f"未找到ID为 {capacity_level_id} 的容量级别")
                    return None
                
                redis_config = RedisConfig.create(
                    capacity_level=level,
                    instance_type=instance_type,
                    memory_gb=memory_gb,
                    bandwidth_gb=bandwidth_gb
                )
                logger.info(f"创建Redis配置成功: {redis_config}")
                return redis_config
        except pw.IntegrityError:
            logger.error(f"Redis配置已存在: {capacity_level_id}")
            return None
        except Exception as e:
            logger.error(f"创建Redis配置失败: {str(e)}")
            return None
    
    def get_redis_config(self, capacity_level_id=None, id=None):
        """获取Redis配置"""
        try:
            if id is not None:
                return RedisConfig.get_or_none(RedisConfig.id == id)
            elif capacity_level_id is not None:
                return RedisConfig.get_or_none(RedisConfig.capacity_level == capacity_level_id)
            else:
                return list(RedisConfig.select())
        except Exception as e:
            logger.error(f"查询Redis配置失败: {str(e)}")
            return None
    
    def update_redis_config(self, id, instance_type=None, memory_gb=None, bandwidth_gb=None):
        """更新Redis配置"""
        try:
            with db.atomic():
                redis_config = RedisConfig.get_or_none(RedisConfig.id == id)
                if not redis_config:
                    logger.error(f"未找到ID为 {id} 的Redis配置")
                    return False
                
                if instance_type is not None:
                    redis_config.instance_type = instance_type
                if memory_gb is not None:
                    redis_config.memory_gb = memory_gb
                if bandwidth_gb is not None:
                    redis_config.bandwidth_gb = bandwidth_gb
                
                redis_config.save()
                logger.info(f"更新Redis配置成功: {redis_config}")
                return True
        except Exception as e:
            logger.error(f"更新Redis配置失败: {str(e)}")
            return False
    
    def delete_redis_config(self, id):
        """删除Redis配置"""
        try:
            with db.atomic():
                redis_config = RedisConfig.get_or_none(RedisConfig.id == id)
                if not redis_config:
                    logger.error(f"未找到ID为 {id} 的Redis配置")
                    return False
                
                redis_config.delete_instance()
                logger.info(f"删除Redis配置成功: ID={id}")
                return True
        except Exception as e:
            logger.error(f"删除Redis配置失败: {str(e)}")
            return False
    
    # ============= PostgresConfig 操作 =============
    def create_postgres_config(self, capacity_level_id, instance_type=None, cpu=None, memory_gb=None):
        """创建Postgres配置"""
        try:
            with db.atomic():
                level = CapacityLevel.get_or_none(CapacityLevel.id == capacity_level_id)
                if not level:
                    logger.error(f"未找到ID为 {capacity_level_id} 的容量级别")
                    return None
                
                pg_config = PostgresConfig.create(
                    capacity_level=level,
                    instance_type=instance_type,
                    cpu=cpu,
                    memory_gb=memory_gb
                )
                logger.info(f"创建Postgres配置成功: {pg_config}")
                return pg_config
        except pw.IntegrityError:
            logger.error(f"Postgres配置已存在: {capacity_level_id}")
            return None
        except Exception as e:
            logger.error(f"创建Postgres配置失败: {str(e)}")
            return None
    
    def get_postgres_config(self, capacity_level_id=None, id=None):
        """获取Postgres配置"""
        try:
            if id is not None:
                return PostgresConfig.get_or_none(PostgresConfig.id == id)
            elif capacity_level_id is not None:
                return PostgresConfig.get_or_none(PostgresConfig.capacity_level == capacity_level_id)
            else:
                return list(PostgresConfig.select())
        except Exception as e:
            logger.error(f"查询Postgres配置失败: {str(e)}")
            return None
    
    def update_postgres_config(self, id, instance_type=None, cpu=None, memory_gb=None):
        """更新Postgres配置"""
        try:
            with db.atomic():
                pg_config = PostgresConfig.get_or_none(PostgresConfig.id == id)
                if not pg_config:
                    logger.error(f"未找到ID为 {id} 的Postgres配置")
                    return False
                
                if instance_type is not None:
                    pg_config.instance_type = instance_type
                if cpu is not None:
                    pg_config.cpu = cpu
                if memory_gb is not None:
                    pg_config.memory_gb = memory_gb
                
                pg_config.save()
                logger.info(f"更新Postgres配置成功: {pg_config}")
                return True
        except Exception as e:
            logger.error(f"更新Postgres配置失败: {str(e)}")
            return False
    
    def delete_postgres_config(self, id):
        """删除Postgres配置"""
        try:
            with db.atomic():
                pg_config = PostgresConfig.get_or_none(PostgresConfig.id == id)
                if not pg_config:
                    logger.error(f"未找到ID为 {id} 的Postgres配置")
                    return False
                
                pg_config.delete_instance()
                logger.info(f"删除Postgres配置成功: ID={id}")
                return True
        except Exception as e:
            logger.error(f"删除Postgres配置失败: {str(e)}")
            return False
    
    # ============= 完整配置操作 =============
    def get_complete_config(self, user_capacity):
        """获取指定用户容量的完整配置信息"""
        try:
            # 查找最接近但不小于指定用户容量的级别
            level = CapacityLevel.select().where(
                CapacityLevel.user_capacity >= user_capacity
            ).order_by(CapacityLevel.user_capacity).first()
            
            if not level:
                logger.error(f"未找到满足用户容量 {user_capacity} 的配置级别")
                return None
            
            # 获取相关配置
            services = list(ServiceConfig.select().where(
                ServiceConfig.capacity_level == level.id
            ))
            redis = RedisConfig.get_or_none(RedisConfig.capacity_level == level.id)
            postgres = PostgresConfig.get_or_none(PostgresConfig.capacity_level == level.id)
            
            # 构建配置字典
            config = {
                "capacity_level": model_to_dict(level),
                "services": [model_to_dict(service) for service in services],
                "redis": model_to_dict(redis) if redis else None,
                "postgres": model_to_dict(postgres) if postgres else None
            }
            
            return config
        except Exception as e:
            logger.error(f"获取完整配置失败: {str(e)}")
            return None