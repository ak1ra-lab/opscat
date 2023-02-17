#! /bin/bash
# author: ak1ra
# date: 2021-04-16
# delete orphan deployments/pods older than 1 days, default pattern is 'telepresence'.

hash kubectl 2>/dev/null || { echo >&2 "Required command 'kubectl' is not installed. Aborting."; exit 1; }
hash xargs 2>/dev/null || { echo >&2 "Required command 'xargs' is not installed. Aborting."; exit 1; }

parallel=10

function kube_delete_orphan_pods() {
    local pattern="$1"
    local namespace="$2"

    deployments="$(kubectl -n $namespace get deployments.apps | awk '/'$pattern'/ && $NF ~ /d/ {print $1}')"
    if [ -n "$deployments" ]; then
        echo $deployments | tr ' ' '\n' | xargs -P$parallel -L1 kubectl -n $namespace delete deployments.apps
    fi

    pods="$(kubectl -n $namespace get pods | awk '/'$pattern'/ && $NF ~ /d/ {print $1}')"
    if [ -n "$pods" ]; then
        echo $pods | tr ' ' '\n' | xargs -P$parallel -L1 kubectl -n $namespace delete pods
    fi
}

pattern="$1"
test -n "$pattern" || pattern="telepresence"

namespace="$2"
if [ -z "$namespace" ]; then
    namespace="$(kubectl config view --minify --output 'jsonpath={..namespace}')"
fi

kube_delete_orphan_pods "$pattern" "$namespace"
