import yaml
import inspect
import os
from lib.logger import app_logger as logger


def get_project_root():
    """获取项目根目录的绝对路径"""
    # 通过当前文件位置推断项目根目录
    current_file = os.path.abspath(inspect.getfile(inspect.currentframe()))
    utils_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(utils_dir)  # 假设当前文件位于项目的utils目录
    return project_root


def load_config(config_file='config.yaml'):
    """
    加载配置文件

    Args:
        config_file: 配置文件路径，可以是相对于项目根目录的路径，也可以是绝对路径

    Returns:
        dict: 配置字典
    """
    # 如果是相对路径，则基于项目根目录解析
    if not os.path.isabs(config_file):
        project_root = get_project_root()
        config_path = os.path.join(project_root, config_file)
    else:
        config_path = config_file

    # 检查文件是否存在
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    # 读取YAML文件
    with open(config_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)

    return config


# 使用示例
try:
    # 直接从项目根目录加载
    config = load_config('config.yaml')

    # 也可以加载子目录中的配置
    # config = load_config('configs/production.yaml')

    # 或者使用绝对路径
    # config = load_config('/path/to/your/config.yaml')

    # PROPERTY_ID = 'properties/348548631'
    # KEY_FILE_LOCATION = r"D:\PycharmProjects\eks-pool-allocator\analytics-read-user.json"

    PROPERTY_ID = config["property_id"]
    KEY_FILE_LOCATION = config["key_file_location"]
    AWS_REGION = config["aws_region"]
    AWS_ACCESS_KEY_ID = config["aws_access_key_id"]
    AWS_SECRET_ACCESS_KEY = config["aws_secret_access_key"]
    RDS_CLUSTER_NAME = config["rds_cluster_name"]
    REDIS_OSS_NAME = config["redis_oss_name"]
    EKS_CLUSTER_NAME = config["eks_cluster_name"]
    CLUSTER_CONTEXT = config["cluster_context"]
    KUBE_FILE_PATH = config["kube_file_path"]
    MYSQL_HOST = config["mysql_host"]
    MYSQL_PORT = config["mysql_port"]
    MYSQL_USER = config["mysql_user"]
    MYSQL_PWD = config["mysql_pwd"]
    MYSQL_DB = config["mysql_db"]
    FEISHU_WEBHOOK_URL = config["feishu_webhook_url"]
    HPA_NAME = config["hpa_name"]
    HPA_NAMESPACE = config["hpa_namespace"]
    HPA_SERVICE_NAME = config["hpa_service_name"]
    CHECK_TIME = config["check_time"]

except Exception as e:
    logger.error("conf -- 加载配置失败")
    print(f"加载配置失败: {e}")



# FEISHU_SECRET
# NAMESPACE = config["k8s_namespace"]