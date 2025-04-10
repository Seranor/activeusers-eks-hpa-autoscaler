import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.models import db,ServiceConfig,RedisConfig,PostgresConfig,CapacityLevel



def initialize_data():
    # 创建表
    db.connect()
    db.create_tables([CapacityLevel, ServiceConfig, RedisConfig, PostgresConfig])
    
    # 清空现有数据
    ServiceConfig.delete().execute()
    RedisConfig.delete().execute()
    PostgresConfig.delete().execute()
    CapacityLevel.delete().execute()
    
    # 容量级别数据保持不变
    capacity_data = [
        {"level": 600, "redis": "cache.m6g.large", "redis_mem": 6, "redis_bw": 10, "pg": "db.r7g.large", "pg_cpu": 2, "pg_mem": 16},
        {"level": 1000, "redis": "cache.c7gn.xlarge", "redis_mem": 6, "redis_bw": 40, "pg": "db.r5.8xlarge", "pg_cpu": 32, "pg_mem": 256},
        {"level": 2000, "redis": "cache.c7gn.xlarge", "redis_mem": 6, "redis_bw": 40, "pg": "db.r5.8xlarge", "pg_cpu": 32, "pg_mem": 256},
        {"level": 3000, "redis": "cache.c7gn.xlarge", "redis_mem": 6, "redis_bw": 40, "pg": "db.r5.8xlarge", "pg_cpu": 32, "pg_mem": 256},
        {"level": 4000, "redis": "cache.c7gn.xlarge", "redis_mem": 6, "redis_bw": 40, "pg": "db.r5.12xlarge", "pg_cpu": 48, "pg_mem": 384},
        {"level": 5000, "redis": "cache.c7gn.xlarge", "redis_mem": 6, "redis_bw": 40, "pg": "db.r5.12xlarge", "pg_cpu": 48, "pg_mem": 384},
        {"level": 6000, "redis": "cache.c7gn.2xlarge", "redis_mem": 12, "redis_bw": 50, "pg": "db.r5.16xlarge", "pg_cpu": 64, "pg_mem": 512},
        {"level": 7000, "redis": "cache.c7gn.2xlarge", "redis_mem": 12, "redis_bw": 50, "pg": "db.r5.16xlarge", "pg_cpu": 64, "pg_mem": 512},
        {"level": 8000, "redis": "cache.c7gn.2xlarge", "redis_mem": 12, "redis_bw": 50, "pg": "db.r5.24xlarge", "pg_cpu": 96, "pg_mem": 768},
        {"level": 9000, "redis": "cache.c7gn.2xlarge", "redis_mem": 12, "redis_bw": 50, "pg": "db.r5.24xlarge", "pg_cpu": 96, "pg_mem": 768},
        {"level": 10000, "redis": "cache.c7gn.2xlarge", "redis_mem": 12, "redis_bw": 50, "pg": "db.r5.24xlarge", "pg_cpu": 96, "pg_mem": 768},
        {"level": 11000, "redis": "cache.c7gn.4xlarge", "redis_mem": 24, "redis_bw": 50, "pg": "db.r5.24xlarge", "pg_cpu": 96, "pg_mem": 768},
        {"level": 12000, "redis": "cache.c7gn.4xlarge", "redis_mem": 24, "redis_bw": 50, "pg": "db.r6i.32xlarge", "pg_cpu": 128, "pg_mem": 1024},
        {"level": 13000, "redis": "cache.c7gn.4xlarge", "redis_mem": 24, "redis_bw": 50, "pg": "db.r6i.32xlarge", "pg_cpu": 128, "pg_mem": 1024},
        {"level": 14000, "redis": "cache.c7gn.4xlarge", "redis_mem": 24, "redis_bw": 50, "pg": "db.r6i.32xlarge", "pg_cpu": 128, "pg_mem": 1024},
        {"level": 15000, "redis": "cache.c7gn.4xlarge", "redis_mem": 24, "redis_bw": 50, "pg": "db.r6i.32xlarge", "pg_cpu": 128, "pg_mem": 1024},
        {"level": 16000, "redis": "cache.c7gn.4xlarge", "redis_mem": 24, "redis_bw": 50, "pg": "db.r7i.48xlarge", "pg_cpu": 192, "pg_mem": 1536},
        {"level": 17000, "redis": "cache.c7gn.4xlarge", "redis_mem": 24, "redis_bw": 50, "pg": "db.r7i.48xlarge", "pg_cpu": 192, "pg_mem": 1536},
        {"level": 18000, "redis": "cache.c7gn.4xlarge", "redis_mem": 24, "redis_bw": 50, "pg": "db.r7i.48xlarge", "pg_cpu": 192, "pg_mem": 1536},
        {"level": 19000, "redis": "cache.c7gn.4xlarge", "redis_mem": 24, "redis_bw": 50, "pg": "db.r7i.48xlarge", "pg_cpu": 192, "pg_mem": 1536},
        {"level": 20000, "redis": "cache.c7gn.4xlarge", "redis_mem": 24, "redis_bw": 50, "pg": "db.r7i.48xlarge", "pg_cpu": 192, "pg_mem": 1536},
    ]
    
    
    # 更新服务副本数配置，包含namespace、hpa名称和节点亲和性
    service_configs = {
        600: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 2, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 2, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 2, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 2, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 2, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 2, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        1000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 4, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 2, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 3, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 4, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 8, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 2, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        2000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 6, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 3, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 6, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 8, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 12, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 3, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        3000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 8, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 4, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 9, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 12, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 16, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 4, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        4000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 10, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 5, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 12, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 16, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 20, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 5, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        5000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 12, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 6, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 15, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 20, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 24, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 6, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        6000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 14, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 7, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 18, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 24, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 28, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 7, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        7000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 16, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 8, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 21, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 28, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 32, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 8, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        8000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 18, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 9, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 24, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 32, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 36, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 9, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        9000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 20, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 10, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 27, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 36, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 40, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 10, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        10000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 22, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 11, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 30, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 40, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 44, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 11, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        11000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 24, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 12, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 33, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 44, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 48, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 12, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        12000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 26, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 13, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 36, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 48, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 52, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 13, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        13000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 28, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 14, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 39, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 52, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 56, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 14, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        14000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 30, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 15, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 42, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 56, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 60, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 15, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        15000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 32, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 16, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 45, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 60, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 64, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 16, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        16000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 34, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 17, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 48, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 64, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 68, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 17, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        17000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 36, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 18, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 51, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 68, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 72, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 18, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        18000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 38, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 19, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 54, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 72, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 76, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 19, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        19000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 40, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 20, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 57, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 76, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 80, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 20, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
        20000: [
            {"namespace": "istio-system", "service": "istio-ingressgateway", "replicas": 42, "hpa": "ingressgateway-hpa", "pool": None},
            {"namespace": "app-production", "service": "gateway-service-be", "replicas": 21, "hpa": "gateway-service-be-hpa", "pool": None},
            {"namespace": "app-production", "service": "web-fe", "replicas": 60, "hpa": "web-fe-hpa", "pool": "pool-web"},
            {"namespace": "app-production", "service": "hermes-service-be", "replicas": 80, "hpa": "hermes-service-be-hpa", "pool": "pool-hermes"},
            {"namespace": "app-production", "service": "passport-be", "replicas": 84, "hpa": "passport-be-hpa", "pool": "pool-passport"},
            {"namespace": "app-production", "service": "project-service-be", "replicas": 21, "hpa": "project-service-be-hpa", "pool": "pool-web"},
        ],
    }
    
    # 使用事务进行批量插入
    with db.atomic():
        # 插入数据
        for data in capacity_data:
            # 创建容量级别
            level = CapacityLevel.create(user_capacity=data["level"])
            
            # 创建Redis配置
            RedisConfig.create(
                capacity_level=level,
                instance_type=data["redis"],
                memory_gb=data["redis_mem"],
                bandwidth_gb=data["redis_bw"]
            )
            
            # 创建Postgres配置
            PostgresConfig.create(
                capacity_level=level,
                instance_type=data["pg"],
                cpu=data["pg_cpu"],
                memory_gb=data["pg_mem"]
            )
            
            # 创建各服务配置
            for service_config in service_configs[data["level"]]:
                ServiceConfig.create(
                    capacity_level=level,
                    service_name=service_config["service"],
                    namespace=service_config["namespace"],
                    replicas=service_config["replicas"],
                    hpa_name=service_config["hpa"],
                    pool_name=service_config["pool"]
                )
    
    db.close()

if __name__ == '__main__':
    # 初始化数据
    initialize_data()