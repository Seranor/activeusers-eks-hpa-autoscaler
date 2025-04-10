import peewee as pw
from playhouse.shortcuts import model_to_dict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.logger import app_logger as logger
from conf import settings
import pymysql
pymysql.install_as_MySQLdb()
# 数据库连接
db = pw.MySQLDatabase(settings.MYSQL_DB, user=settings.MYSQL_USER, password=settings.MYSQL_PWD, 
                       host=settings.MYSQL_HOST, port=settings.MYSQL_PORT)

# 基础模型类
class BaseModel(pw.Model):
    class Meta:
        database = db

# 容量级别模型
class CapacityLevel(BaseModel):
    user_capacity = pw.IntegerField(unique=True, null=False)
    
    def __str__(self):
        return f"CapacityLevel(user_capacity={self.user_capacity})"

# 服务配置模型 - 增加了namespace, hpa_name和pool_name字段
class ServiceConfig(BaseModel):
    capacity_level = pw.ForeignKeyField(CapacityLevel, backref='services', on_delete='CASCADE')
    service_name = pw.CharField(max_length=50, null=False)
    namespace = pw.CharField(max_length=50, default='default')
    replicas = pw.IntegerField(null=False)
    hpa_name = pw.CharField(max_length=100, null=True)  # 新增HPA名称字段
    pool_name = pw.CharField(max_length=50, null=True)  # 新增节点亲和性pool_name字段
    
    class Meta:
        indexes = (
            (('capacity_level', 'service_name', 'namespace'), True),
        )
    
    def __str__(self):
        return f"ServiceConfig(namespace={self.namespace}, service={self.service_name}, replicas={self.replicas})"

# Redis配置模型
class RedisConfig(BaseModel):
    capacity_level = pw.ForeignKeyField(CapacityLevel, backref='redis_config', on_delete='CASCADE')
    instance_type = pw.CharField(max_length=50, null=True)
    memory_gb = pw.FloatField(null=True)
    bandwidth_gb = pw.FloatField(null=True)
    
    def __str__(self):
        return f"RedisConfig(instance_type={self.instance_type}, memory={self.memory_gb}GB)"

# Postgres配置模型
class PostgresConfig(BaseModel):
    capacity_level = pw.ForeignKeyField(CapacityLevel, backref='postgres_config', on_delete='CASCADE')
    instance_type = pw.CharField(max_length=50, null=True)
    cpu = pw.IntegerField(null=True)
    memory_gb = pw.IntegerField(null=True)
    
    def __str__(self):
        return f"PostgresConfig(instance_type={self.instance_type}, cpu={self.cpu}, memory={self.memory_gb}GB)"
