# k8s 客户端
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
from typing import Dict, List, Optional, Union, Any
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.logger import app_logger as logger


class K8sClient:
    """
    面向对象的Kubernetes客户端，用于操作K8s集群资源，
    特别是Deployment的节点调度和HPA配置
    """

    def __init__(self, kube_config_path: Optional[str] = None, context_name: Optional[str] = None):
        """
        初始化K8s客户端

        Args:
            kube_config_path: kubeconfig文件的路径，默认为None，会使用~/.kube/config
            context_name: 要使用的context名称，默认为None，会使用当前context
        """
        self.kube_config_path = kube_config_path or os.path.expanduser("~/.kube/config")
        self.context_name = context_name

        try:
            if self.context_name:
                config.load_kube_config(config_file=self.kube_config_path, context=self.context_name)
            else:
                config.load_kube_config(config_file=self.kube_config_path)

            # 初始化各种API客户端
            self.apps_api = client.AppsV1Api()
            self.core_api = client.CoreV1Api()
            self.autoscaling_api = client.AutoscalingV2Api()  # 使用V2版本以支持更多配置

            logger.info(f"k8s -- 成功初始化K8s客户端，使用配置文件: {self.kube_config_path}")
            if self.context_name:
                logger.info(f"k8s -- `使用context: {self.context_name}")
        except Exception as e:
            logger.error(f"k8s -- 初始化K8s客户端失败: {str(e)}")
            raise
    
    # 获取deployment信息
    def get_deployment(self, name: str, namespace: str = "default"):
        """
        获取指定Deployment的详细信息

        Args:
            name: Deployment名称
            namespace: 命名空间，默认为'default'

        Returns:
            V1Deployment: Deployment对象
        """
        try:
            return self.apps_api.read_namespaced_deployment(name=name, namespace=namespace)
        except ApiException as e:
            logger.error(f"k8s -- 获取Deployment '{name}'失败: {str(e)}")
            raise

    def get_deployment_pod_count(self, deployment_name: str, namespace: str = "default"):
        """
        获取指定Deployment的Pod数量

        Args:
            deployment_name: Deployment名称
            namespace: 命名空间，默认为'default'

        Returns:
            Dict: 包含总Pod数、可用Pod数和准备就绪Pod数的字典
        """
        try:
            deployment = self.get_deployment(deployment_name, namespace)

            # 获取deployment的标签选择器
            label_selector = ""
            for key, value in deployment.spec.selector.match_labels.items():
                if label_selector:
                    label_selector += ","
                label_selector += f"{key}={value}"

            # 使用标签选择器查询关联的pod
            pods = self.core_api.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector
            )

            total_pods = len(pods.items)
            ready_pods = sum(1 for pod in pods.items if self._is_pod_ready(pod))

            # 获取deployment状态
            replicas = deployment.status.replicas or 0
            available_replicas = deployment.status.available_replicas or 0
            ready_replicas = deployment.status.ready_replicas or 0

            result = {
                "desired_replicas": deployment.spec.replicas,
                "current_replicas": replicas,
                "available_replicas": available_replicas,
                "ready_replicas": ready_replicas,
                "total_pods": total_pods,
                "ready_pods": ready_pods
            }

            logger.info(f"k8s -- 已查询Deployment '{deployment_name}'的Pod数量: {result}")
            return result
        except ApiException as e:
            logger.error(f"k8s -- 获取Deployment '{deployment_name}'的Pod数量失败: {str(e)}")
            raise

    def _is_pod_ready(self, pod):
        """
        判断Pod是否就绪

        Args:
            pod: Pod对象

        Returns:
            bool: Pod是否就绪
        """
        # 检查Pod的状态阶段
        if pod.status.phase != "Running":
            return False

        # 检查是否所有容器都就绪
        if not pod.status.container_statuses:
            return False

        return all(container.ready for container in pod.status.container_statuses)

    def get_deployment_node_affinity(self, deployment_name: str, namespace: str = "default"):
        """
        获取Deployment的节点亲和性配置

        Args:
            deployment_name: Deployment名称
            namespace: 命名空间，默认为'default'

        Returns:
            V1NodeAffinity: 节点亲和性配置对象，没有则返回None
        """
        try:
            # 获取当前Deployment
            deployment = self.get_deployment(deployment_name, namespace)

            # 获取node affinity配置
            affinity = deployment.spec.template.spec.affinity
            if affinity and affinity.node_affinity:
                logger.info(f"k8s -- 获取到Deployment '{deployment_name}'的节点亲和性配置")
                return affinity.node_affinity
            else:
                logger.info(f"k8s -- Deployment '{deployment_name}'没有节点亲和性配置")
                return None
        except ApiException as e:
            logger.error(f"k8s -- 获取Deployment '{deployment_name}'的节点亲和性配置失败: {str(e)}")
            raise

    def set_nodegroup_affinity(self, deployment_name: str, nodegroup_key: str, nodegroup_values: str, namespace: str = "default"):
        """
        设置Deployment的节点组亲和性

        Args:
            deployment_name: Deployment名称
            nodegroup_name: 节点组名称
            namespace: 命名空间，默认为'default'

        Returns:
            V1Deployment: 更新后的Deployment对象
        """
        try:
            # 创建nodeAffinity配置
            patch = {
                "spec": {
                    "template": {
                        "spec": {
                            "affinity": {
                                "nodeAffinity": {
                                    "requiredDuringSchedulingIgnoredDuringExecution": {
                                        "nodeSelectorTerms": [
                                            {
                                                "matchExpressions": [
                                                    {
                                                        "key": nodegroup_key,
                                                        "operator": "In",
                                                        "values": [nodegroup_values]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            # 应用更新
            updated_deployment = self.apps_api.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=patch
            )

            logger.success(f"k8s -- 成功为Deployment '{deployment_name}'设置节点组亲和性: {nodegroup_key}={nodegroup_values}")
            return updated_deployment
        except ApiException as e:
            logger.error(f"k8s -- 为Deployment '{deployment_name}'设置节点组亲和性失败: {str(e)}")
            raise
            
    def remove_node_affinity(self, deployment_name: str, namespace: str = "default"):
        """
        完全移除Deployment的节点亲和性配置

        Args:
            deployment_name: Deployment名称
            namespace: 命名空间，默认为'default'

        Returns:
            V1Deployment: 更新后的Deployment对象
        """
        try:
            # 移除整个affinity
            patch = {
                "spec": {
                    "template": {
                        "spec": {
                            "affinity": None
                        }
                    }
                }
            }
            
            # 应用更新
            updated_deployment = self.apps_api.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=patch
            )

            logger.success(f"k8s -- 成功从Deployment '{deployment_name}'移除所有节点亲和性配置")
            return updated_deployment
        except ApiException as e:
            logger.error(f"k8s -- 从Deployment '{deployment_name}'移除节点亲和性配置失败: {str(e)}")
            raise

    # HPA相关操作
    def get_hpa(self, name: str, namespace: str = "default"):
        """
        获取HPA配置

        Args:
            name: HPA名称
            namespace: 命名空间，默认为'default'

        Returns:
            V2HorizontalPodAutoscaler: HPA对象
        """
        try:
            return self.autoscaling_api.read_namespaced_horizontal_pod_autoscaler(
                name=name,
                namespace=namespace
            )
        except ApiException as e:
            logger.error(f"k8s -- 获取HPA '{name}'失败: {str(e)}")
            raise

    def update_hpa_scaling(self, hpa_name: str, min_replicas: Optional[int] = None,
                           max_replicas: Optional[int] = None, namespace: str = "default"):
        """
        更新HPA的最小和最大副本数

        Args:
            hpa_name: HPA名称
            min_replicas: 最小副本数，None表示不更改
            max_replicas: 最大副本数，None表示不更改
            namespace: 命名空间，默认为'default'

        Returns:
            V2HorizontalPodAutoscaler: 更新后的HPA对象
        """
        try:
            # 获取当前HPA
            hpa = self.get_hpa(hpa_name, namespace)

            # 准备patch
            patch = {"spec": {}}

            if min_replicas is not None:
                patch["spec"]["minReplicas"] = min_replicas

            if max_replicas is not None:
                patch["spec"]["maxReplicas"] = max_replicas

            # 只有当有更改时才应用patch
            if patch["spec"]:
                updated_hpa = self.autoscaling_api.patch_namespaced_horizontal_pod_autoscaler(
                    name=hpa_name,
                    namespace=namespace,
                    body=patch
                )

                changes = []
                if min_replicas is not None:
                    changes.append(f"min_replicas={min_replicas}")
                if max_replicas is not None:
                    changes.append(f"max_replicas={max_replicas}")

                logger.success(f"k8s -- 成功更新HPA '{hpa_name}': {', '.join(changes)}")
                return updated_hpa
            else:
                logger.warning(f"k8s -- 没有为HPA '{hpa_name}'提供任何更改")
                return hpa
        except ApiException as e:
            logger.error(f"k8s -- 更新HPA '{hpa_name}'失败: {str(e)}")
            raise

    def get_hpa_scaling_config(self, hpa_name: str, namespace: str = "default"):
        """
        获取HPA的扩缩容配置

        Args:
            hpa_name: HPA名称
            namespace: 命名空间，默认为'default'

        Returns:
            Dict: 包含min_replicas和max_replicas的字典
        """
        try:
            hpa = self.get_hpa(hpa_name, namespace)
            result = {
                "min_replicas": hpa.spec.min_replicas,
                "max_replicas": hpa.spec.max_replicas,
                "metrics": hpa.spec.metrics
            }
            # logger.info(f"k8s -- HPA '{hpa_name}'的扩缩容配置: {result}")
            return result
        except ApiException as e:
            logger.error(f"k8s -- 获取HPA '{hpa_name}'的扩缩容配置失败: {str(e)}")
            raise


if __name__ == '__main__':
    # 创建K8s客户端实例
    k8s_client = K8sClient(
        kube_config_path="~/.kube/config",
        context_name="arn:aws:eks:us-east-2:xxx:cluster/app-pre"
    )

    # 查询Pod数量示例
    # try:
    #     pod_count_info = k8s_client.get_deployment_pod_count(
    #         deployment_name="web-fe",
    #         namespace="app-pre"
    #     )
    #     print(f"Deployment详情:")
    #     print(f"- 期望副本数: {pod_count_info['desired_replicas']}")
    #     print(f"- 当前副本数: {pod_count_info['current_replicas']}")
    #     print(f"- 可用副本数: {pod_count_info['available_replicas']}")
    #     print(f"- 就绪副本数: {pod_count_info['ready_replicas']}")
    #     print(f"- 总Pod数: {pod_count_info['total_pods']}")
    #     print(f"- 就绪Pod数: {pod_count_info['ready_pods']}")
    # except Exception as e:
    #     print(f"查询Pod数量失败: {str(e)}")


    # 节点亲和性示例
    try:
        # 查询节点亲和性
        node_affinity = k8s_client.get_deployment_node_affinity(
            deployment_name="web-fe",
            namespace="app-pre"
        )
        
        # 提取nodegroup表达式为字典格式
        nodegroup_expr = None
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
        
        if nodegroup_expr:
            print(f"当前节点组亲和性: {nodegroup_expr}")
            print(nodegroup_expr.get('key'))
            print(nodegroup_expr.get('values'))



            # 输出示例: 当前节点组亲和性: {'key': 'eks.amazonaws.com/nodegroup', 'operator': 'In', 'values': ['pool-web']}
        else:
            print("未配置节点组亲和性")
        
        
        # 设置节点组亲和性示例
        # k8s_client.set_nodegroup_affinity(
        #     deployment_name="web-fe",
        #     namespace="app-pre",
        #     nodegroup_key="eks.amazonaws.com/nodegroup",
        #     nodegroup_values="pool-web" 
        # )  # 只能设置一个，会被替换掉，不能设置为  eks.amazonaws.com/nodegroup=pool-web    eks.amazonaws.com/nodegroup=pool-hermes
        
        # 移除节点亲和性示例
        # k8s_client.remove_node_affinity(
        #     deployment_name="web-fe",
        #     namespace="app-pre"
        # )

    except Exception as e:
        print(f"节点亲和性操作失败: {str(e)}")


    # HPA示例
    # try:
        # 更新HPA配置
        # k8s_client.update_hpa_scaling(
        #     hpa_name="hermes-service-be-hpa",
        #     min_replicas=4,
        #     max_replicas=6,
        #     namespace="app-pre"
        # )

        # 查询HPA配置
        # hpa_config = k8s_client.get_hpa_scaling_config(
        #     hpa_name="ingressgateway-hpa",
        #     namespace="istio-system"
        # )
        # print(f"HPA配置: 最小副本数={hpa_config['min_replicas']}, 最大副本数={hpa_config['max_replicas']}")
    # except Exception as e:
    #     print(f"HPA操作失败: {str(e)}")
