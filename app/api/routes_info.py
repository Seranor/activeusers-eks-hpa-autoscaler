from . import api_blueprint
from flask import jsonify

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conf import settings
from lib.logger import app_logger as logger
from lib.get_analytics_user import get_active_users
from lib.aws_db import AWSDBManager
from lib.aws_eks import EKSManager
from lib.k8s_client import K8sClient
from lib.query_data import ScalingConfigManager



@api_blueprint.route('/status')
def status_info():
    '''获取当前在线人数、数据库配置、EKS节点信息以及deployment的信息'''
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

    scaling_manager = ScalingConfigManager()

    user_count = get_active_users(settings.KEY_FILE_LOCATION, settings.PROPERTY_ID)

    redis_node_type = aws_db_manager.get_elasticache_redis_node_type(settings.REDIS_OSS_NAME)
    rds_instance_types = aws_db_manager.get_rds_cluster_instance_type(settings.RDS_CLUSTER_NAME)
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
    rds_highest_type = highest_type

    
    nodegroups = aws_eks_manager.list_nodegroups()
    node_info = {}

    for nodegroup_name in nodegroups:
        desired_size = aws_eks_manager.get_nodegroup_desired_size(nodegroup_name)
        node_info[nodegroup_name] = desired_size

    k8s_dep_info = []
    k8s_affinity = []


    complete_config = scaling_manager.get_complete_config(user_count)

    nodegroup_expr = None
    for namespace, services in complete_config["services"].items(): 
        for service_name, service_config in services.items(): 
            pod_count_info = k8s_client.get_deployment_pod_count(
                deployment_name=service_name,
                namespace=namespace
            )
            hpa_config = k8s_client.get_hpa_scaling_config(
                hpa_name=service_config['hpa_name'],
                namespace=namespace
            )

            k8s_dep_info.append({
                    service_name:pod_count_info['current_replicas'],
                    service_config['hpa_name']:hpa_config['min_replicas']
                })
            
            if service_config.get('pool_name'):
                node_affinity = k8s_client.get_deployment_node_affinity(
                    deployment_name=service_name,
                    namespace=namespace
                )
                # print(service_config.get('pool_name'))
                if node_affinity and node_affinity.required_during_scheduling_ignored_during_execution:
                    node_selector_terms = node_affinity.required_during_scheduling_ignored_during_execution.node_selector_terms
                    if node_selector_terms:
                        for term in node_selector_terms:
                            if term.match_expressions:
                                for expr in term.match_expressions:
                                    if expr.key == "eks.amazonaws.com/nodegroup":
                                        nodegroup_expr = {
                                            'key': expr.key,
                                            'operator': expr.operator,
                                            'values': expr.values
                                        }
                                        break
                # print(nodegroup_expr)
                if nodegroup_expr:
                    # print(f"当前节点组亲和性: {nodegroup_expr}")
                    # print(nodegroup_expr.get('key'))
                    # print(nodegroup_expr.get('values'))
                    k8s_affinity.append({service_name:nodegroup_expr.get('values')})

    return jsonify({
        "active_user": user_count,
        "db_conf":{"RDS":rds_highest_type,"Redis":redis_node_type},
        "eks_node":node_info,
        "k8s_dep_info":k8s_dep_info,
        "k8s_affinity":k8s_affinity
        }), 200