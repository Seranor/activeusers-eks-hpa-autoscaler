### 功能
根据google https://analytics.google.com/ 的在线人数

实现更新EKS中指定HPA的指定大小

### 配置文件
```yaml
property_id: "properties/xxx"
key_file_location: "/project/analytics-read-user.json"
aws_region: "us-east-2"
aws_access_key_id: ""
aws_secret_access_key: ""
rds_cluster_name: ""
redis_oss_name: ""
eks_cluster_name: ""
cluster_context: "arn:aws:eks:us-east-2:xxxxxx:cluster/"
kube_file_path: "~/.kube/config"
feishu_webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx"
mysql_host: ""
mysql_port: 3306
mysql_user: ""
mysql_pwd: ""
mysql_db: ""
hpa_name: "ingressgateway-hpa"
hpa_namespace: "istio-system"
hpa_service_name: "istio-ingressgateway"
check_time: 5
```
| 配置              | 作用                             |
| ----------------- | -------------------------------- |
| property_id       | google analytics中的id           |
| key_file_location | google analytics的auth文件       |
| cluster_context   | k8s的context name                |
| kube_file_path    | k8s kube文件默认是~/.kube/config |
| hpa_name          | 判断当前级别的hpa名称            |
| hpa_service_name  | hpa对应的服务                    |
| check_time        | 检查间隔 分钟级别                |

### 使用
#### 级别设置
| 在线容纳人数范围 | istio-ingress | gateway | web  | hermes | passport | project | Redis实例类型     | 内存 | 带宽 | 实例类型       | CPU/内存 |
| ---------------- | ------------- | ------- | ---- | ------ | -------- | ------- | ----------------- | ---- | ---- | -------------- | -------- |
| 600（默认）      | 2             | 2       | 2    | 2      | 2        | 2       | cache.m6g.large   | 6G   | 10G  | db.r7g.large   | 2C16G    |
| 1000             | 4             | 2       | 3    | 4      | 8        | 2       | cache.c7gn.xlarge | 6G   | 40G  | db.r5.8xlarge  | 32C256G  |
| 2000             | 6             | 3       | 6    | 8      | 12       | 3       |                   |      |      |                |          |
| 3000             | 8             | 4       | 9    | 12     | 16       | 4       |                   |      |      |                |          |
| 4000             | 10            | 5       | 12   | 16     | 20       | 5       |                   |      |      | db.r5.12xlarge | 48C384G  |
| 5000             | 12            | 6       | 15   | 20     | 24       | 6       |                   |      |      |                |          |

```python
# 提前准备好数据库账号密码 创建好库
# 文件根据该配置初始化配置
# 初始化数据库
python lib/initial_data.py
```
扩容hpa的时候会检查DB配置信息是否符合，不符合会发送通知提醒升级，当符合配置后才会修改HPA配置
#### mock 模拟测试

```python
# 创建模拟环境
python3 -m venv myenv

# 安装依赖
pip install -r requirements.txt 

# 模拟测试
python mock/mock.py

'''
# mock.py 文件中说明
INITIAL_USERS = 6 # 初始人数
GROWTH_RATE = 3 # 增长间隔
PAUSE_THRESHOLDS = [500,600,1000, 2000, 3000, 4000]  # 需要暂停的人数节点


/api/status  # 信息
/api/reset   # 重置人数
/api/continue-growth # 继续增长人数
/api/online-users    # 当前人数

'''

# 修改 core/core.py 文件中方法 check_and_scale 中的  user_count 注释上get_active_users  打开 get_mock_users(api_url=(api_url="http://IP:5000/api/online-users")

# 运行程序
python run.py
```

#### 正常运行
```python
# 修改正确的配置文件
# 安装依赖
pip install -r requirements.txt 

# 运行
python main.py
```

#### 接口说明
本身提供了一些接口

/api/upgrade/<int:capacity>
直接升级到指定级别配置，升级前提配置需要得到满足，降级不需要DB配置满足 600 会直接删除亲和性等


/api/status
状态查询接口

还提供了更新上述级别配置的接口