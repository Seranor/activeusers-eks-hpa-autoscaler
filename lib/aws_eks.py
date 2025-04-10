# 实现EKS节点池配置模块
import boto3
from botocore.exceptions import ClientError
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.logger import app_logger as logger


class EKSManager:
    """
    AWS EKS集群管理工具类，用于管理EKS集群的节点组配置
    """

    def __init__(self, region_name, access_key_id, secret_access_key, cluster_name):
        """
        初始化EKS管理器

        Args:
            region_name (str): AWS区域名称
            access_key_id (str): AWS访问密钥ID
            secret_access_key (str): AWS秘密访问密钥
            cluster_name (str): EKS集群名称
        """
        logger.info(f"aws eks -- 初始化EKS管理器，连接到集群: {cluster_name} 区域: {region_name}")
        try:
            self.client = boto3.client('eks',
                                       region_name=region_name,
                                       aws_access_key_id=access_key_id,
                                       aws_secret_access_key=secret_access_key)
            self.cluster_name = cluster_name
            self._validate_cluster()
        except ClientError as e:
            logger.error(f"aws eks -- 初始化EKS客户端失败: {str(e)}")
            raise

    def _validate_cluster(self):
        """验证集群是否存在且可访问"""
        try:
            response = self.client.describe_cluster(name=self.cluster_name)
            logger.debug(f"aws eks -- 成功连接到集群 {self.cluster_name}, 状态: {response['cluster']['status']}")
            return True
        except ClientError as e:
            logger.error(f"aws eks -- 验证集群 {self.cluster_name} 失败: {str(e)}")
            raise ValueError(f"aws eks -- 无法访问集群 {self.cluster_name}: {str(e)}")

    def update_nodegroup_scaling(self, nodegroup, min_size, max_size, desired_size):
        """
        更新EKS节点组的伸缩配置

        Args:
            nodegroup (str): 节点组名称
            min_size (int): 最小节点数量
            max_size (int): 最大节点数量
            desired_size (int): 期望节点数量

        Returns:
            bool: 操作是否成功
        """
        logger.info(f"aws eks -- 更新节点组 {nodegroup} 伸缩配置: min={min_size}, max={max_size}, desired={desired_size}")

        # 获取当前配置用于记录变化
        current_config = self._get_nodegroup_scaling_config(nodegroup)
        if current_config:
            logger.info(
                f"aws eks -- 当前配置: min={current_config['minSize']}, max={current_config['maxSize']}, desired={current_config['desiredSize']}")

        try:
            response = self.client.update_nodegroup_config(
                clusterName=self.cluster_name,
                nodegroupName=nodegroup,
                scalingConfig={
                    'minSize': min_size,
                    'maxSize': max_size,
                    'desiredSize': desired_size
                }
            )

            status_code = response['ResponseMetadata']['HTTPStatusCode']
            if status_code == 200:
                logger.info(f"aws eks -- 成功提交节点组 {nodegroup} 伸缩配置更新请求")
                return True
            else:
                logger.warning(f"aws eks -- 更新请求返回非200状态码: {status_code}")
                return False

        except ClientError as e:
            logger.error(f"aws eks -- 更新节点组 {nodegroup} 伸缩配置失败: {str(e)}")
            return False

    def _get_nodegroup_scaling_config(self, nodegroup_name):
        """获取节点组的伸缩配置"""
        try:
            response = self.client.describe_nodegroup(
                clusterName=self.cluster_name,
                nodegroupName=nodegroup_name
            )
            if 'nodegroup' in response and 'scalingConfig' in response['nodegroup']:
                return response['nodegroup']['scalingConfig']
            return None
        except ClientError as e:
            logger.error(f"aws eks -- 获取节点组 {nodegroup_name} 配置失败: {str(e)}")
            return None

    def get_nodegroup_desired_size(self, nodegroup_name):
        """
        获取指定节点组的期望节点数量

        Args:
            nodegroup_name (str): 节点组名称

        Returns:
            int|None: 期望节点数量，获取失败则返回None
        """
        logger.debug(f"aws eks -- 获取节点组 {nodegroup_name} 的期望节点数量")
        try:
            response = self.client.describe_nodegroup(
                clusterName=self.cluster_name,
                nodegroupName=nodegroup_name
            )
            if 'nodegroup' in response and 'scalingConfig' in response['nodegroup']:
                size = response['nodegroup']['scalingConfig']['desiredSize']
                logger.debug(f"aws eks -- 节点组 {nodegroup_name} 的期望节点数量: {size}")
                return size
            logger.warning(f"aws eks -- 获取节点组 {nodegroup_name} 信息时未找到伸缩配置")
            return None
        except ClientError as e:
            logger.error(f"aws eks -- 获取节点组 {nodegroup_name} 信息失败: {str(e)}")
            return None

    def list_nodegroups(self):
        """
        列出EKS集群中所有节点组的名称

        Returns:
            list: 节点组名称列表
        """
        logger.info(f"aws eks -- 获取集群 {self.cluster_name} 的所有节点组")
        try:
            response = self.client.list_nodegroups(clusterName=self.cluster_name)
            nodegroups = response.get('nodegroups', [])
            logger.info(f"aws eks -- 找到 {len(nodegroups)} 个节点组")
            logger.debug(f"aws eks -- 节点组列表: {nodegroups}")
            return nodegroups
        except ClientError as e:
            logger.error(f"aws eks -- 获取节点组列表失败: {str(e)}")
            return []

    def get_nodegroup_status(self, nodegroup_name):
        """
        获取节点组的状态

        Args:
            nodegroup_name (str): 节点组名称

        Returns:
            str|None: 节点组状态，或在获取失败时返回None
        """
        logger.debug(f"aws eks -- 获取节点组 {nodegroup_name} 的状态")
        try:
            response = self.client.describe_nodegroup(
                clusterName=self.cluster_name,
                nodegroupName=nodegroup_name
            )
            if 'nodegroup' in response and 'status' in response['nodegroup']:
                status = response['nodegroup']['status']
                logger.debug(f"aws eks -- 节点组 {nodegroup_name} 的状态: {status}")
                return status
            return None
        except ClientError as e:
            logger.error(f"aws eks -- 获取节点组 {nodegroup_name} 状态失败: {str(e)}")
            return None

    def get_all_nodegroups_info(self):
        """
        获取所有节点组的详细信息

        Returns:
            dict: 节点组信息字典，键为节点组名称
        """
        logger.info(f"aws eks -- 获取集群 {self.cluster_name} 所有节点组的详细信息")
        result = {}
        nodegroups = self.list_nodegroups()

        for nodegroup in nodegroups:
            try:
                response = self.client.describe_nodegroup(
                    clusterName=self.cluster_name,
                    nodegroupName=nodegroup
                )
                if 'nodegroup' in response:
                    result[nodegroup] = response['nodegroup']
                    logger.debug(f"aws eks -- 已获取节点组 {nodegroup} 的详细信息")
            except ClientError as e:
                logger.error(f"aws eks -- 获取节点组 {nodegroup} 详细信息失败: {str(e)}")

        logger.info(f"aws eks -- 成功获取 {len(result)} 个节点组的详细信息")
        return result


if __name__ == '__main__':
    from conf import settings
    eks_manager = EKSManager(settings.AWS_REGION, settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.EKS_CLUSTER_NAME)

    nodegroups = eks_manager.list_nodegroups()

    node_info = {}

    for nodegroup_name in nodegroups:
        desired_size = eks_manager.get_nodegroup_desired_size(nodegroup_name)
        node_info[nodegroup_name] = desired_size

    print(node_info)

    for pool in node_info:
        if node_info[pool] == 0:
            print(pool)
            # up_pool_state = eks_manager.update_nodegroup_scaling(pool,0,20,0)
    # 更新节点数
    # state = eks_manager.update_nodegroup_scaling("pool-01",3,3,3)
