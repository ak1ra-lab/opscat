#! /bin/bash
# author: ak1ra
# date: 2021-03-23

hash kubectl 2>/dev/null || { echo >&2 "Required command 'kubectl' is not installed. Aborting."; exit 1; }

function menu() {
    for idx in ${!pods[@]}; do
        printf "%3d | %s\n" "$((idx+1))" "${pods[$idx]}"
    done
}

namespace="$2"
if [ -z "$namespace" ]; then
    namespace="$(kubectl config view --minify --output 'jsonpath={..namespace}')"
fi

pattern="$1"
if [ -n "$pattern" ]; then
    pods=($(kubectl -n "$namespace" get pods | awk 'NR>1 && /'$pattern'/ {print $1}'))
else
    pods=($(kubectl -n "$namespace" get pods | awk 'NR>1 {print $1}'))
fi

menu
read -p "请根据索引选择 Pod: " choice
echo $choice | egrep -q '[1-9][0-9]?'
if [ $? -eq 0 ]; then
    eval "kubectl -n \"$namespace\" exec -it \"${pods[$((choice-1))]}\" -- bash"
fi
