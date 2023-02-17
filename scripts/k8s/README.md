
# README for scripts/k8s/*

关于各个脚本的简要说明:

```
scripts/k8s/docker-rm.sh                  # 给定搜索 pattern 删除多余 docker 镜像
scripts/k8s/kube-delete-orphan-pods.sh    # 给定搜索 pattern 删除足够旧的, 孤立的 Deployments/Pods 资源, 默认 pattern 是 telepresence
scripts/k8s/kube-desc-node.sh             # 获取集群所有 node 的 kubectl describe node 的 Allocated resources 段后的后 10 行内容
scripts/k8s/kube-exec-pod.sh              # 用于在 Kubernetes master 节点快速执行 kubectl exec 命令进入某个 pod
scripts/k8s/kube-join-nodes.sh            # 用于给 Kubernetes 集群新增 node, 通过 ssh 在 node 上执行 kubeadm join 命令
scripts/k8s/kube-kubeconfig-selector.sh   # 用于添加至 ~/.bashrc 快速设置 `KUBECONFIG` 环境变量
scripts/k8s/tke-kube-user.sh              # 用于在 TKE 集群中使用多 Service 复用 LoadBalancer 特性自行开启 TKE 集群内网访问
```
