#! /bin/bash
# author: ak1ra
# date: 2021-04-16
# kubernetes join nodes
# Update:
#   * 2021-11-22: add --control-plane flag support

hash kubeadm 2>/dev/null || { echo >&2 "Required command 'kubeadm' is not installed. Aborting."; exit 1; }
hash openssl 2>/dev/null || { echo >&2 "Required command 'openssl' is not installed. Aborting."; exit 1; }
hash awk 2>/dev/null || { echo >&2 "Required command 'awk' is not installed. Aborting."; exit 1; }
hash ssh 2>/dev/null || { echo >&2 "Required command 'ssh' is not installed. Aborting."; exit 1; }

node_list="$1"
test -n "$node_list" || exit 1

is_control_plane="$2"
test -n "$is_control_plane" || is_control_plane=false

token="$(kubeadm token create)"
hash="$(openssl x509 -pubkey -in /etc/kubernetes/pki/ca.crt | openssl rsa -pubin -outform der 2>/dev/null | openssl dgst -sha256 -hex | sed 's/^.* //')"

apiserver="$(awk -F/ '/server/ {print $NF}' /etc/kubernetes/admin.conf)"

join_cmd="kubeadm join $apiserver --token $token --discovery-token-ca-cert-hash sha256:$hash"
if [ "$is_control_plane" == "true" ]; then
    certificate_key="$(kubeadm alpha certs certificate-key)"
    join_cmd="$join_cmd --control-plane --certificate-key $certificate_key"
fi

echo $join_cmd

choice=n
read -p "Continue to add node_list: $node_list into cluster? [y/N] " choice
choice=$(echo $choice | tr "A-Z" "a-z")
if [ "$choice" == "y" -o "$choice" == "yes" ]; then
    for node in $(echo $node_list | tr ',' ' '); do
        ssh $node "$join_cmd"
    done
else
    kubeadm token delete $token
fi
