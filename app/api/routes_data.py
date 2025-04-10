from flask import request, jsonify
from functools import wraps
from . import api_blueprint

# 导入之前定义的 CapacityConfigManager
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.update_data import CapacityConfigManager
from lib.logger import app_logger as logger

config_manager = CapacityConfigManager()

# 辅助函数: 响应包装器
def api_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if isinstance(result, tuple) and len(result) == 2:
                data, code = result
            else:
                data, code = result, 200
                
            return jsonify({
                "status": "success",
                "data": data
            }), code
        except Exception as e:
            logger.error(f"API错误: {str(e)}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    return wrapper

# ==================== CapacityLevel API ====================
@api_blueprint.route('/capacity_levels', methods=['GET'])
@api_response
def get_capacity_levels():
    """获取所有容量级别"""
    levels = config_manager.get_capacity_level()
    return [{"id": level.id, "user_capacity": level.user_capacity} for level in levels]

@api_blueprint.route('/capacity_levels/<int:id>', methods=['GET'])
@api_response
def get_capacity_level(id):
    """获取特定容量级别"""
    level = config_manager.get_capacity_level(id=id)
    if not level:
        return {"message": f"未找到ID为 {id} 的容量级别"}, 404
    return {"id": level.id, "user_capacity": level.user_capacity}

@api_blueprint.route('/capacity_levels', methods=['POST'])
@api_response
def create_capacity_level():
    """创建新的容量级别"""
    data = request.get_json()
    if not data or 'user_capacity' not in data:
        return {"message": "缺少必要参数: user_capacity"}, 400
    
    user_capacity = data['user_capacity']
    level = config_manager.create_capacity_level(user_capacity)
    
    if not level:
        return {"message": f"创建容量级别失败，用户容量 {user_capacity} 可能已存在"}, 400
    
    return {"id": level.id, "user_capacity": level.user_capacity}, 201

@api_blueprint.route('/capacity_levels/<int:id>', methods=['PUT'])
@api_response
def update_capacity_level(id):
    """更新容量级别"""
    data = request.get_json()
    if not data or 'user_capacity' not in data:
        return {"message": "缺少必要参数: user_capacity"}, 400
    
    success = config_manager.update_capacity_level(id, data['user_capacity'])
    
    if not success:
        return {"message": f"更新容量级别失败，ID {id} 不存在或用户容量已被使用"}, 400
    
    level = config_manager.get_capacity_level(id=id)
    return {"id": level.id, "user_capacity": level.user_capacity}

@api_blueprint.route('/capacity_levels/<int:id>', methods=['DELETE'])
@api_response
def delete_capacity_level(id):
    """删除容量级别"""
    success = config_manager.delete_capacity_level(id)
    
    if not success:
        return {"message": f"删除容量级别失败，ID {id} 不存在"}, 404
    
    return {"message": f"容量级别 {id} 已成功删除"}

# ==================== ServiceConfig API ====================
@api_blueprint.route('/services', methods=['GET'])
@api_response
def get_all_services():
    """获取所有服务配置"""
    services = config_manager.get_service_config()
    return [format_service(service) for service in services]

@api_blueprint.route('/capacity_levels/<int:capacity_id>/services', methods=['GET'])
@api_response
def get_level_services(capacity_id):
    """获取特定容量级别的所有服务配置"""
    services = config_manager.get_service_config(capacity_level_id=capacity_id)
    if services is None:
        return {"message": f"获取服务配置失败或容量级别 {capacity_id} 不存在"}, 404
    return [format_service(service) for service in services]

@api_blueprint.route('/services/<int:id>', methods=['GET'])
@api_response
def get_service(id):
    """获取特定服务配置"""
    service = config_manager.get_service_config(id=id)
    if not service:
        return {"message": f"未找到ID为 {id} 的服务配置"}, 404
    return format_service(service)

@api_blueprint.route('/services', methods=['POST'])
@api_response
def create_service():
    """创建新的服务配置"""
    data = request.get_json()
    required_fields = ['capacity_level_id', 'service_name', 'namespace', 'replicas']
    
    for field in required_fields:
        if field not in data:
            return {"message": f"缺少必要参数: {field}"}, 400
    
    service = config_manager.create_service_config(
        capacity_level_id=data['capacity_level_id'],
        service_name=data['service_name'],
        namespace=data['namespace'],
        replicas=data['replicas'],
        hpa_name=data.get('hpa_name'),
        pool_name=data.get('pool_name')
    )
    
    if not service:
        return {"message": "创建服务配置失败，请检查容量级别ID是否存在"}, 400
    
    return format_service(service), 201

@api_blueprint.route('/services/<int:id>', methods=['PUT'])
@api_response
def update_service(id):
    """更新服务配置"""
    data = request.get_json()
    success = config_manager.update_service_config(
        id=id,
        replicas=data.get('replicas'),
        hpa_name=data.get('hpa_name'),
        pool_name=data.get('pool_name')
    )
    
    if not success:
        return {"message": f"更新服务配置失败，ID {id} 不存在"}, 404
    
    service = config_manager.get_service_config(id=id)
    return format_service(service)

@api_blueprint.route('/services/<int:id>', methods=['DELETE'])
@api_response
def delete_service(id):
    """删除服务配置"""
    success = config_manager.delete_service_config(id)
    
    if not success:
        return {"message": f"删除服务配置失败，ID {id} 不存在"}, 404
    
    return {"message": f"服务配置 {id} 已成功删除"}

# ==================== RedisConfig API ====================
@api_blueprint.route('/redis', methods=['GET'])
@api_response
def get_all_redis_configs():
    """获取所有Redis配置"""
    configs = config_manager.get_redis_config()
    return [format_redis(config) for config in configs]

@api_blueprint.route('/capacity_levels/<int:capacity_id>/redis', methods=['GET'])
@api_response
def get_level_redis(capacity_id):
    """获取特定容量级别的Redis配置"""
    config = config_manager.get_redis_config(capacity_level_id=capacity_id)
    if not config:
        return {"message": f"未找到容量级别 {capacity_id} 的Redis配置"}, 404
    return format_redis(config)

@api_blueprint.route('/redis/<int:id>', methods=['GET'])
@api_response
def get_redis(id):
    """获取特定Redis配置"""
    config = config_manager.get_redis_config(id=id)
    if not config:
        return {"message": f"未找到ID为 {id} 的Redis配置"}, 404
    return format_redis(config)

@api_blueprint.route('/redis', methods=['POST'])
@api_response
def create_redis():
    """创建新的Redis配置"""
    data = request.get_json()
    if 'capacity_level_id' not in data:
        return {"message": "缺少必要参数: capacity_level_id"}, 400
    
    config = config_manager.create_redis_config(
        capacity_level_id=data['capacity_level_id'],
        instance_type=data.get('instance_type'),
        memory_gb=data.get('memory_gb'),
        bandwidth_gb=data.get('bandwidth_gb')
    )
    
    if not config:
        return {"message": "创建Redis配置失败，请检查容量级别ID是否存在"}, 400
    
    return format_redis(config), 201

@api_blueprint.route('/redis/<int:id>', methods=['PUT'])
@api_response
def update_redis(id):
    """更新Redis配置"""
    data = request.get_json()
    success = config_manager.update_redis_config(
        id=id,
        instance_type=data.get('instance_type'),
        memory_gb=data.get('memory_gb'),
        bandwidth_gb=data.get('bandwidth_gb')
    )
    
    if not success:
        return {"message": f"更新Redis配置失败，ID {id} 不存在"}, 404
    
    config = config_manager.get_redis_config(id=id)
    return format_redis(config)

@api_blueprint.route('/redis/<int:id>', methods=['DELETE'])
@api_response
def delete_redis(id):
    """删除Redis配置"""
    success = config_manager.delete_redis_config(id)
    
    if not success:
        return {"message": f"删除Redis配置失败，ID {id} 不存在"}, 404
    
    return {"message": f"Redis配置 {id} 已成功删除"}

# ==================== PostgresConfig API ====================
@api_blueprint.route('/postgres', methods=['GET'])
@api_response
def get_all_postgres_configs():
    """获取所有Postgres配置"""
    configs = config_manager.get_postgres_config()
    return [format_postgres(config) for config in configs]

@api_blueprint.route('/capacity_levels/<int:capacity_id>/postgres', methods=['GET'])
@api_response
def get_level_postgres(capacity_id):
    """获取特定容量级别的Postgres配置"""
    config = config_manager.get_postgres_config(capacity_level_id=capacity_id)
    if not config:
        return {"message": f"未找到容量级别 {capacity_id} 的Postgres配置"}, 404
    return format_postgres(config)

@api_blueprint.route('/postgres/<int:id>', methods=['GET'])
@api_response
def get_postgres(id):
    """获取特定Postgres配置"""
    config = config_manager.get_postgres_config(id=id)
    if not config:
        return {"message": f"未找到ID为 {id} 的Postgres配置"}, 404
    return format_postgres(config)

@api_blueprint.route('/postgres', methods=['POST'])
@api_response
def create_postgres():
    """创建新的Postgres配置"""
    data = request.get_json()
    if 'capacity_level_id' not in data:
        return {"message": "缺少必要参数: capacity_level_id"}, 400
    
    config = config_manager.create_postgres_config(
        capacity_level_id=data['capacity_level_id'],
        instance_type=data.get('instance_type'),
        cpu=data.get('cpu'),
        memory_gb=data.get('memory_gb')
    )
    
    if not config:
        return {"message": "创建Postgres配置失败，请检查容量级别ID是否存在"}, 400
    
    return format_postgres(config), 201

@api_blueprint.route('/postgres/<int:id>', methods=['PUT'])
@api_response
def update_postgres(id):
    """更新Postgres配置"""
    data = request.get_json()
    success = config_manager.update_postgres_config(
        id=id,
        instance_type=data.get('instance_type'),
        cpu=data.get('cpu'),
        memory_gb=data.get('memory_gb')
    )
    
    if not success:
        return {"message": f"更新Postgres配置失败，ID {id} 不存在"}, 404
    
    config = config_manager.get_postgres_config(id=id)
    return format_postgres(config)

@api_blueprint.route('/postgres/<int:id>', methods=['DELETE'])
@api_response
def delete_postgres(id):
    """删除Postgres配置"""
    success = config_manager.delete_postgres_config(id)
    
    if not success:
        return {"message": f"删除Postgres配置失败，ID {id} 不存在"}, 404
    
    return {"message": f"Postgres配置 {id} 已成功删除"}

# ==================== 完整配置 API ====================
@api_blueprint.route('/config/<int:user_capacity>', methods=['GET'])
@api_response
def get_config_for_capacity(user_capacity):
    """获取适合特定用户容量的完整配置"""
    config = config_manager.get_complete_config(user_capacity)
    
    if not config:
        return {"message": f"未找到适合用户容量 {user_capacity} 的配置"}, 404
    
    return config

# ==================== 辅助格式化函数 ====================
def format_service(service):
    """格式化服务配置为JSON格式"""
    return {
        "id": service.id,
        "capacity_level_id": service.capacity_level.id,
        "service_name": service.service_name,
        "namespace": service.namespace,
        "replicas": service.replicas,
        "hpa_name": service.hpa_name,
        "pool_name": service.pool_name
    }

def format_redis(config):
    """格式化Redis配置为JSON格式"""
    return {
        "id": config.id,
        "capacity_level_id": config.capacity_level.id,
        "instance_type": config.instance_type,
        "memory_gb": config.memory_gb,
        "bandwidth_gb": config.bandwidth_gb
    }

def format_postgres(config):
    """格式化Postgres配置为JSON格式"""
    return {
        "id": config.id,
        "capacity_level_id": config.capacity_level.id,
        "instance_type": config.instance_type,
        "cpu": config.cpu,
        "memory_gb": config.memory_gb
    }