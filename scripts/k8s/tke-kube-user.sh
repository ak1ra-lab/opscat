#! /bin/bash
# author: ak1ra
# date: 2021-12-30
# 使用多 Service 复用 LoadBalancer 特性自行开启 TKE 集群内网访问, 该特性需要提工单开启
# 关键在于创建一个跟 kube-user Service 同名的 Endpoints 资源指向 apiserver
# apiserver endpoints 的 (ip, port) 来自于 /api/v1/namespaces/default/endpoints/kubernetes
# ref: https://cloud.tencent.com/document/product/457/46370

hash kubectl 2>/dev/null || { echo >&2 "Required command 'kubectl' is not installed. Aborting."; exit 1; }

function gen_kube_user_yaml() {
    cat <<EOF
---
apiVersion: v1
kind: Endpoints
metadata:
  labels:
    component: apiserver
    provider: kubernetes
  name: kube-user-lb
subsets:
  - addresses:
      - ip: ${endpoint_ip}
    ports:
      - name: https
        port: ${endpoint_port}
        protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.kubernetes.io/tke-existed-lbid: ${ingress_lb_id}
  labels:
    component: apiserver
    provider: kubernetes
  name: kube-user-lb
spec:
  type: LoadBalancer
  externalTrafficPolicy: Cluster
  sessionAffinity: None
  ports:
    - name: https
      port: ${apiserver_port}
      protocol: TCP
      targetPort: ${endpoint_port}
EOF
}

apiserver_port=6443

kubeconfig="$1"
test -n "$kubeconfig" || { echo >&2 "kubeconfig can not be empty. Aborting."; exit 1; }

ingress_type="$2"
test -n "$ingress_type" || ingress_type=traefik

if [ "$ingress_type" == "traefik" ]; then
    ingress_svc="/api/v1/namespaces/traefik-tke/services/traefik-traefik-tke-httplocal"
elif [ "$ingress_type" == "nginx" ]; then
    ingress_svc="/api/v1/namespaces/kube-system/services/nginx-ingress-local-ingress-nginx-controller"
else
    echo >&2 "unknown ingress type: $ingress_type"
    exit 1
fi

ingress_ip=$(kubectl --kubeconfig $kubeconfig get --raw $ingress_svc | jq -r '.status.loadBalancer.ingress[0].ip')
ingress_lb_id=$(kubectl --kubeconfig $kubeconfig get --raw $ingress_svc | jq -r '.metadata.annotations."service.kubernetes.io/loadbalance-id"')
test -n "$ingress_ip" || exit 1

endpoint_ip=$(kubectl --kubeconfig $kubeconfig get --raw /api/v1/namespaces/default/endpoints/kubernetes | jq -r '.subsets[0].addresses[0].ip')
endpoint_port=$(kubectl --kubeconfig $kubeconfig get --raw /api/v1/namespaces/default/endpoints/kubernetes | jq -r '.subsets[0].ports[0].port')

kubeconfig_basename=$(basename $kubeconfig | cut -d. -f1)
gen_kube_user_yaml | tee ${kubeconfig_basename}.yaml | kubectl --kubeconfig $kubeconfig -n default apply -f -

# 修改 KUBECONFIG 附加端口号
sed -i -r '/\s+server:/s%(cls-\w{8}\.ccs\.tencent-cloud\.com)$%\1:'$apiserver_port'%' $kubeconfig

# 修改 /etc/hosts
cluster_id=$(perl -n -e '/(cls-\w{8})\.ccs\.tencent-cloud\.com/ && print $1' $kubeconfig)
sed -i -r '/'$cluster_id'/s%^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}%'$ingress_ip'%' /etc/hosts
