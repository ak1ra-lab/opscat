
# opscat

DevOps (cat) tools

## quick start

使用 `pip` 安装 `opscat`.

> 暂未上传至 PyPI, 需要下载到本地后执行 `pip` 命令安装.

```shell
git clone https://github.com/ak1ra-lab/opscat.git && cd optcat/
python3 -m pip --update pip && pip install .
```

## [alidns](opscat/alidns/alidns.py)

> 经原私有仓库脱敏后开源, 迁移前为单文件可执行脚本

执行 `alidns --help` 查看使用帮助, 或者查看 [README for alidns.py](opscat/alidns/README.md)

## [tls-secret-helper](opscat/tls_secret_helper/tls_secret_helper.py)

> 经原私有仓库脱敏后开源, 迁移前为单文件可执行脚本

执行 `tls-secret-helper --help` 查看使用帮助, 或者查看 [README for tls-secret-helper](opscat/tls_secret_helper/README.md)

## [etcdadm-secret-helper.sh](scripts/etcdadm-cert-helper/etcdadm-cert-helper.sh)

查看 [README for etcdadm-secret-helper.sh](scripts/etcdadm-cert-helper/README.md) 获取详细帮助

## [tls-selfsigned-cert.sh](scripts/tls-selfsigned-cert/tls-selfsigned-cert.sh)

使用 [cloudflare/cfssl](https://github.com/cloudflare/cfssl) 快速创建自签名 CA 和用该 CA 签名的证书

## TODO

* [ ] 目前收录的脚本大多为单文件可执行脚本, 之后考虑拆分为不同模块的多文件.
