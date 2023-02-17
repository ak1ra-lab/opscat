#! /bin/bash
# author: ak1ra
# date: 2021-04-27
# helper script to create new cert signed by existing CA
#     with existing cert key for etcd cluster created by etcdadm tool
# ref: https://www.digitalocean.com/community/tutorials/openssl-essentials-working-with-ssl-certificates-private-keys-and-csrs

# # 查看 csr 信息
# openssl req -text -noout -in apiserver-etcd-client.csr
# # 查看 cert 信息
# openssl x509 -text -noout -in apiserver-etcd-client.crt

cert_dir="/etc/kubernetes/pki/etcd"
ip_addr="$(ip r get 1 | awk 'NR==1 {print $NF}')"

# subject
apiserver_subj="/C=/ST=/L=/O=system:masters/CN=$(hostname)-kube-apiserver-etcd-client"
etcdctl_subj="/C=/ST=/L=/O=system:masters/CN=$(hostname)-etcdctl"
peer_subj="/C=/ST=/L=/O=/CN=$(hostname)"
server_subj="/C=/ST=/L=/O=/CN=$(hostname)"

# x509_extensions
# ref: https://www.openssl.org/docs/manmaster/man5/x509v3_config.html
keyUsage="keyUsage=digitalSignature,keyEncipherment"
peerSAN="subjectAltName=DNS:$(hostname),IP:${ip_addr}"
serverSAN="${peerSAN},IP:127.0.0.1"

apiserver_ext="${keyUsage}\nextendedKeyUsage=clientAuth"
etcdctl_ext="${keyUsage}\nextendedKeyUsage=clientAuth"
peer_ext="${keyUsage}\nextendedKeyUsage=clientAuth,serverAuth\n${peerSAN}"
server_ext="${keyUsage}\nextendedKeyUsage=clientAuth,serverAuth\n${serverSAN}"

function sign_cert() {
    local_component="$1"
    local_subj="$2"
    local_extfile="$3"
    local_days="$4"
    test -n "$local_days" || local_days=1825

    # 使用现有 key 创建 csr
    openssl req \
        -key ${cert_dir}/${local_component}.key \
        -subj "$local_subj" \
        -new -out ${local_component}.csr

    # openssl req -text -noout -in ${local_component}.csr
    # read -p "Continue to sign ${local_component}.crt? " choice

    # 使用 csr 签发证书
    openssl x509 \
        -req -days ${local_days} -sha256 -in ${local_component}.csr \
        -CA ${cert_dir}/ca.crt -CAkey ${cert_dir}/ca.key -CAcreateserial \
        -extfile <(printf "$local_extfile") \
        -out ${local_component}.crt

    # 显示刚签发的证书信息
    openssl x509 -text -noout -in ${local_component}.crt
    read -p "Continue? " choice
}

sign_cert "apiserver-etcd-client" "$apiserver_subj" "$apiserver_ext"
sign_cert "etcdctl-etcd-client" "$etcdctl_subj" "$etcdctl_ext"
sign_cert "peer" "$peer_subj" "$peer_ext"
sign_cert "server" "$server_subj" "$server_ext"
