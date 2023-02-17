
# README for etcdadm-secret-helper.sh

## [etcdadm](https://github.com/kubernetes-sigs/etcdadm) 工具创建的 etcd 集群证书更新问题

在写这个脚本时还不会用 [cloudflare/cfssl](https://github.com/cloudflare/cfssl), 这里是查找了很多资料后用 openssl 工具完成的.

## 脚本 [etcdadm-cert-helper.sh](etcdadm-cert-helper.sh)

首先复习一些 tls 相关知识:

> crt 用于消息加密, 需要公开能让 client 获取到, client 或 peer 需要用 crt 对消息加密,
> key 用于消息解密, 一定要保密, server/peer 或 client 收到对方使用自己的 crt 加密的消息后用自己的 key 对消息解密.

编写了一个脚本用于更新由 etcdadm 创建的 etcd cluster 的 tls 证书, etcdadm 这个工具创建的集群默认配置下开启了 client-to-server, peer-to-peer 的双向 tls 认证, 也即 etcd server 端需要创建 server, peer 证书, 每个访问 etcd cluster 的客户端也需要创建自己的证书, 这里的客户端有 apiserver 和 etcdctl. 这些证书都由最开始创建的 ca.key 签发.

apiserver 和 etcdctl 的客户端证书有配置 Organization 和 Common Name subject, server 和 peer 证书除了设置了 Common Name 外还有 subjectAltName, 这些证书都有设置 X.509 v3 的 extendedKeyUsage 中的 clientAuth 和 serverAuth.

因此使用 openssl 工具签发证书时除了添加 subject 字段外还需要添加 X.509 v3 的一些扩展字段. 之前因为不懂证书签发的原理, 因此看到 Cloudflare 提供的 cfssl 工具反而觉得不好用, 在搜索"怎么使用 openssl 添加扩展字段"的过程中发现 openssl 这个工具真的不好用. 当然觉得不好用的根本原因是对这个领域很多概念都不懂, 回头看下 cfssl 的使用, 目前这个脚本使用 openssl 完成证书签发过程.

## etcd 集群证书用途分析

最初在使用 [etcdadm](https://github.com/kubernetes-sigs/etcdadm) 工具快速创建 etcd cluster 时所执行的命令为:

```
# mkdir -p /data

# etcdadm init --certs-dir /etc/kubernetes/pki/etcd/ --install-dir /data/etcd/

复制根证书到 etcd 节点
# rsync -avR /etc/kubernetes/pki/etcd/ca.* example-k8s-etcd02-prod:/
# rsync -avR /etc/kubernetes/pki/etcd/ca.* example-k8s-etcd03-prod:/

在剩下两个节点上各自执行
# etcdadm join --certs-dir /etc/kubernetes/pki/etcd/ --install-dir /data/etcd/ https://10.20.0.16:2379
```

查看之前留下的日志, 发现 etcdadm init 在创建证书时有以下输出:

```
creating a self signed etcd CA certificate and key files
creating a new server certificate and key files for etcd, server serving cert is signed for DNS names example-k8s-etcd01-prod and IPs 10.20.0.16 127.0.0.1
creating a new certificate and key files for etcd peering, peer serving cert is signed for DNS names example-k8s-etcd01-prod and IPs 10.20.0.16
creating a new client certificate for the etcdctl
creating a new client certificate for the apiserver calling etcd
```

简单翻译下的话就是首先创建了 CA, 然后依次创建了 server, peer 服务器证书, 以及 etcdctl 和 apiserver 的客户端证书, 注意这里在签发 server 和 peer 证书时有添加 subjectAltName. 另外需要注意的是, 执行 etcdadm init 时, 工具为第一个节点创建了 ca 和 server, peer, client 证书, 但是只复制了 ca 证书到剩下两个节点, 剩下节点在使用 etcdadm join 时会使用这个 ca 为自己创建专用的 server, peer 和 client 证书.

* keyUsage=digitalSignature,keyEncipherment
* extendedKeyUsage:
    * server & peer: clientAuth, serverAuth
    * etcdctl & apiserver: clientAuth
* subjectAltName:
    * server: DNS:$(hostname),IP:${ip_addr},IP:127.0.0.1
    * peer: DNS:$(hostname),IP:${ip_addr}

生成 csr 时可以不指定 X.509 v3 扩展字段, 在签发的时候使用 `-extfile` 选项传入相关值.

etcdadm 创建的这几对证书用途如下:

```
# tree /etc/kubernetes/pki
/etc/kubernetes/pki
└── etcd
    ├── apiserver-etcd-client.crt    # client certificate for the apiserver calling etcd
    ├── apiserver-etcd-client.key
    ├── ca.crt                       # self signed etcd CA certificate and key files
    ├── ca.key
    ├── etcdctl-etcd-client.crt      # client certificate for the etcdctl
    ├── etcdctl-etcd-client.key
    ├── peer.crt                     # certificate and key files for etcd peering
    ├── peer.key
    ├── server.crt                   # server certificate and key
    └── server.key
```

配合 /etc/etcd/etcd.env 文件的内容, 结合 [Transport security model | etcd](https://etcd.io/docs/v3.3/op-guide/security/) 页面的解释.

```
## 客户端证书认证, 双向认证
ETCD_CLIENT_CERT_AUTH=true
ETCD_CERT_FILE=/etc/kubernetes/pki/etcd/server.crt
ETCD_KEY_FILE=/etc/kubernetes/pki/etcd/server.key
ETCD_TRUSTED_CA_FILE=/etc/kubernetes/pki/etcd/ca.crt

## peer 客户端证书认证, 双向认证
ETCD_PEER_CLIENT_CERT_AUTH=true
ETCD_PEER_CERT_FILE=/etc/kubernetes/pki/etcd/peer.crt
ETCD_PEER_KEY_FILE=/etc/kubernetes/pki/etcd/peer.key
ETCD_PEER_TRUSTED_CA_FILE=/etc/kubernetes/pki/etcd/ca.crt
```

因为开启了 `ETCD_CLIENT_CERT_AUTH` 和 `ETCD_PEER_CLIENT_CERT_AUTH` 选项, 因此 client-to-server, server-to-server 都需要提供各自的证书, 这里创建的所有证书都使用同一个 CA 签发, 因此 `ETCD_TRUSTED_CA_FILE` 和 `ETCD_PEER_TRUSTED_CA_FILE` 也指向了同一个 CA.

## 参考文档

* [Transport security model | etcd](https://etcd.io/docs/v3.3/op-guide/security/)
* [Introducing CFSSL - CloudFlare's PKI toolkit](https://blog.cloudflare.com/introducing-cfssl/)
