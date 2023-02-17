#! /bin/bash
# author: ak1ra
# date: 2021-04-16

hash kubectl 2>/dev/null || { echo >&2 "Required command 'kubectl' is not installed. Aborting."; exit 1; }

desc_tail_max=10

function kubectl_desc_node() {
    local role="$1"
    test -n "$role" || role=node

    local nodes="$(kubectl get nodes --no-headers | awk '/'$role'/ {print $1}')"
    for node in $nodes; do
        echo "========== $node =========="
        kubectl describe node $node | grep -A$desc_tail_max -E '^Allocated resources:'
    done
}

kubectl_desc_node "master"
kubectl_desc_node "node"
