
# README for tls-secret-helper

## 注意

使用 `tls-secret-helper --help` 查看详细帮助信息,
本 README.md 文档可能会忘记更新导致与 `tls-secret-helper --help` 输出不符, 如果出现这样的情况, 请以 `tls-secret-helper --help` 输出的帮助信息为准.

## 快速开始

本脚本用于管理 `--config-file` 中配置的 Kubernetes 集群 TLS Secrets

`--action` 默认值为 `check`, 用于检查 `--certs-dir` 目录下 TLS 证书文件的有效期,

* `--certs-dir` 的默认值为 `/etc/pki/tls-secret-helper`
* `--config-file` 的默认值为 `$CERTS_DIR/config.json`

`$CERTS_DIR` 中 cert 文件名格式为 `${DOMAIN}_bundle.crt`, key 文件名格式为 `${DOMAIN}.key`.

`--config-file` 的格式为:

```json
{
    "example-k8s-test.conf": [
        "example-test.com",
        "example-test.net"
    ],
    "example-k8s-prod.conf": [
        "example.com",
        "example.net"
    ]
}
```

> 其中 `example-k8s-test.conf`, `example-k8s-prod.conf` 为 `$KUBECONFIG_DIR` (默认值 `~/.kube`) 目录下的 `KUBECONFIG` 文件名, 用于指向不同的 Kubernetes 集群.

## 关于 `--action` 选项的额外说明:

    --action add, 添加单个 TLS Secret, 需要同时指定 -k, -d, -n 选项
    --action delete, 删除单个 TLS Secret, 需要同时指定 -k, -d, -n 选项

    --action tls:list, 列出 Kubernetes 集群内的 TLS Secret, 指定 -k 时可只列出特定集群
    --action tls:check, 检查 Kubernetes 集群内 TLS Secret 证书内容有效期,
        可配合 -k, -d, -n 可选参数限定检查范围

    --action tls:add, 批量添加 TLS Secrets, 可配合 -k, -d, -n 可选参数限定操作范围
    --action tls:delete, 批量删除 TLS Secrets, 可配合 -k, -d, -n 可选参数限定操作范围

EXAMPLES:

    为特定集群添加单个证书, 需要同时指定 -k, -d, -n 选项
    $ tls-secret-helper -a add -k ~/.kube/config -d example.com -n default,prod

    只指定 -k 时, -d 从配置文件中读取, -n 默认使用集群中所有命名空间
    $ tls-secret-helper -a tls:add -k ~/.kube/config

    同时指定 -k 和 -d 时, -n 默认使用集群中所有命名空间
    $ tls-secret-helper -a tls:add -k ~/.kube/config -d example.com

    只指定 -d 时, -k 为配置文件中包含该域名的 KUBECONFIG, -n 默认使用集群中所有命名空间
    $ tls-secret-helper -a tls:add -d example.com
