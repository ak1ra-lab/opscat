#! /usr/bin/env python3
# coding: utf-8

import argparse
import base64
import json
import os
import pathlib
import re
import socket
import subprocess
import sys
from datetime import datetime, timedelta

import httpx
from cryptography import x509


def run_shell_cmd(cmd, exit_if_non_zero=False, print_cmd=True):
    if print_cmd:
        sys.stderr.write(f"$ {cmd}\n")
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        sys.stderr.write(stderr.decode())
        if exit_if_non_zero:
            sys.exit(proc.returncode)
    return stdout, stderr


def wechat_bot_send_text(bot_url, message, mentioned_list=[], mentioned_mobile_list=[]):
    data = {
        "msgtype": "text",
        "text": {
            "content": message,
            "mentioned_list": mentioned_list,
            "mentioned_mobile_list": mentioned_mobile_list
        }
    }

    r = httpx.post(bot_url, json=data)
    return r.json()


def check_cert_validation(cert, days,
                          namespace="default", excluded_common_names=[]):
    if isinstance(cert, bytes):
        cert_obj = x509.load_pem_x509_certificate(cert)
        cert_fmt_str = f"namespace/{namespace}\n"
    else:
        with open(cert) as f:
            cert_obj = x509.load_pem_x509_certificate(f.read().encode())
        cert_fmt_str = f"{cert}\n"

    cert_fmt_str += \
        f"    {cert_obj.subject.rfc4514_string()}\n" + \
        f"    Not Before: {cert_obj.not_valid_before}, Not After: {cert_obj.not_valid_after}"

    cn = cert_obj.subject.get_attributes_for_oid(
        x509.NameOID.COMMON_NAME)[0].value
    # 已知 excluded_common_names 中域名已过期且不再续费
    if cn in excluded_common_names:
        return

    if cert_obj.not_valid_after < datetime.now() + timedelta(days=days):
        return cert_fmt_str


def check_certs_dir(certs_dir, days, bot_url=False):
    certs_dir_path = pathlib.Path(certs_dir).expanduser()
    cert_fmt_str_list = []
    for certs_dir_file in os.listdir(certs_dir_path):
        if not certs_dir_file.endswith(".crt"):
            continue
        cert_fmt_str = check_cert_validation(
            certs_dir_path.joinpath(certs_dir_file), days)
        if cert_fmt_str:
            cert_fmt_str_list.append(cert_fmt_str)

    if not len(cert_fmt_str_list) > 0:
        return
    cert_fmt_str_list.append(
        f"以上证书将于 {days} 天内过期, 请及时前往 {socket.gethostname()}:{certs_dir} 目录更新证书文件\n")
    message = "\n".join(cert_fmt_str_list)
    sys.stdout.write(message)

    if bot_url:
        wechat_bot_send_text(bot_url, message.rstrip())


def check_tls_secrets(kubeconfig, namespaces, domain, days, bot_url=None):
    kubectl = f"kubectl --kubeconfig {kubeconfig}"
    secret = "ssl-%s" % domain.replace(".", "-")
    cert_fmt_str_list = []
    for namespace in namespaces:
        cert_cmd = f"{kubectl} -n {namespace} get secrets {secret} -o jsonpath='{{.data.tls\.crt}}'"
        stdout, _ = run_shell_cmd(cert_cmd, exit_if_non_zero=False)
        if not len(stdout) > 0:
            continue
        cert = base64.b64decode(stdout.decode())
        cert_fmt_str = check_cert_validation(cert, days, namespace)
        if cert_fmt_str:
            cert_fmt_str_list.append(cert_fmt_str)

    if not len(cert_fmt_str_list) > 0:
        return
    cert_fmt_str_list.append(
        f"集群 {os.path.basename(kubeconfig)} 内 secret/{secret} 证书将于 {days} 天内过期, 请及时更新\n")
    message = "\n".join(cert_fmt_str_list)
    sys.stdout.write(message)

    if bot_url:
        wechat_bot_send_text(bot_url, message.rstrip())


def tls_secret_helper(kubeconfig, namespaces, domain, action, certs_dir):
    kubeconfig = pathlib.Path(kubeconfig).expanduser() \
        if not isinstance(kubeconfig, pathlib.Path) else kubeconfig
    certs_dir_path = pathlib.Path(certs_dir).expanduser()
    cert = certs_dir_path.joinpath("%s_bundle.crt" % domain)
    key = certs_dir_path.joinpath("%s.key" % domain)
    secret = "ssl-%s" % domain.replace(".", "-")

    for namespace in namespaces:
        kubectl = f"kubectl --kubeconfig {kubeconfig} --namespace {namespace}"
        del_cmd = f"{kubectl} delete secret {secret} --ignore-not-found"
        add_cmd = f"{kubectl} create secret tls {secret} --key {key} --cert {cert}"

        run_shell_cmd(del_cmd, exit_if_non_zero=True)
        if action == "add":
            run_shell_cmd(add_cmd, exit_if_non_zero=True)


def get_namespaces(kubeconfig, args):
    exclude_prefix = r"^(c|p|u|cattle|cluster-fleet|fleet|istio|kube|mesh|rancher|tcr|tke-cluster|user)-"
    exclude_full = r"^(ambassador|kubernetes-dashboard|kuboard|lens-metrics|my-eclipse-che|nacos|operators|spark-operator|tutorial)$"
    kubeconfig = pathlib.Path(kubeconfig).expanduser() \
        if not isinstance(kubeconfig, pathlib.Path) else kubeconfig
    namespaces_cmd = f"kubectl --kubeconfig {kubeconfig} get namespaces -oname"
    stdout, _ = run_shell_cmd(namespaces_cmd, exit_if_non_zero=True)
    namespaces = [ns.strip().split("/")[1] for ns in stdout.decode().split()] \
        if not args.namespaces else [ns.strip() for ns in args.namespaces.split(",")]
    namespaces_filtered = [ns for ns in namespaces
                           if not re.match(exclude_prefix, ns) and not re.match(exclude_full, ns)]

    return namespaces_filtered


def action_tls_wrapper(args):
    try:
        action = args.action.split(":")[1]
    except IndexError:
        action = "list"

    with open(args.config_file, encoding="utf-8") as f:
        config = json.loads(f.read())

    # 获取 kubeconfig
    kubeconfig_dir_default = pathlib.Path("~/.kube").expanduser()
    if args.kubeconfig:
        kubeconfig_list = [pathlib.Path(args.kubeconfig)]
    elif args.domain:
        # 在只指定 domain 的情况下, 将从 config 中获取 kubeconfig
        kubeconfig_list = [kubeconfig_dir_default.joinpath(k)
                           for k, v in config.items() if args.domain in v]
    else:
        kubeconfig_list = [kubeconfig_dir_default.joinpath(
            k) for k in config.keys()]

    # action tls:list
    if action == "list":
        for kubeconfig in kubeconfig_list:
            kubectl = f"kubectl --kubeconfig {kubeconfig}"
            list_cmd = f"{kubectl} get secrets --all-namespaces --field-selector=type=kubernetes.io/tls"
            stdout, _ = run_shell_cmd(list_cmd, exit_if_non_zero=False)
            if not len(stdout) > 0:
                continue
            sys.stdout.write(stdout.decode())
        return

    # action tls:check, tls:add, tls:delete
    for kubeconfig in kubeconfig_list:
        namespaces = get_namespaces(kubeconfig, args)
        domain_key = os.path.basename(kubeconfig) \
            .replace("dev", "test").replace("uat", "prod")
        domains = config.get(domain_key) or [] \
            if not args.domain else [args.domain]
        for domain in domains:
            if action == "check":
                check_tls_secrets(kubeconfig, namespaces,
                                  domain, args.days, args.bot)
            elif action in ["add", "del", "delete"]:
                tls_secret_helper(kubeconfig, namespaces,
                                  domain, action, args.certs_dir)
            else:
                argument_parser().print_help()


def argument_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)
    certs_dir_default = pathlib.Path("/etc/pki/tls-secret-helper")
    config_default = certs_dir_default.joinpath("config.json")
    action_choices = [
        "check", "add", "delete",
        "tls:list", "tls:check", "tls:add", "tls:delete"
    ]
    action_default = action_choices[0]
    epilog = '''
关于 --action 选项的额外说明:

    --action check, 检查 --certs-dir 下证书文件有效期
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
'''

    parser.epilog = epilog
    parser.add_argument("-a", "--action", choices=action_choices,
                        default=action_default, help=f"要对集群内 TLS Secret 执行的操作 (default: %(default)s)")
    parser.add_argument("-C", "--certs-dir", default=certs_dir_default,
                        help=f"域名证书文件目录 (default: %(default)s)")
    parser.add_argument("-f", "--config-file", default=config_default,
                        help=f"要读取的 (kubeconfig, domian) 映射配置文件 (default: %(default)s)")

    parser.add_argument("-k", "--kubeconfig",
                        help="要操作的 Kubernetes 集群的 KUBECONFIG 文件, 默认为空.")
    parser.add_argument("-d", "--domain", help="要添加证书的域名, 默认为空.")
    parser.add_argument("-n", "--namespaces",
                        help="逗号分隔 namespaces 列表, 默认为该集群中所有命名空间.")

    check_group = parser.add_argument_group("--action 为 [check|tls:check] 时")
    check_group.add_argument("--days", default=30, type=int, help="证书过期门限天数")
    check_group.add_argument("--bot", default=None,
                             help="企业微信群机器人 URL, 用于发送证书过期提醒")

    return parser


def main():
    args = argument_parser().parse_args()

    # action check
    if args.action == "check":
        check_certs_dir(args.certs_dir, args.days, args.bot)
        return

    # action: add, delete
    if args.action in ["add", "del", "delete"]:
        # FIXME: 此种情况下 --namespaces 选项是必要的吗?
        if not all([args.kubeconfig, args.domain, args.namespaces]):
            sys.stderr.write("执行 %s 操作时, 必须同时设置 -k, -d, -n 选项\n" % args.action)
            return
        namespaces = get_namespaces(args.kubeconfig, args)
        tls_secret_helper(args.kubeconfig, namespaces,
                          args.domain, args.action, args.certs_dir)
        return

    # action tls:list, tls:add, tls:delete
    if args.action.startswith("tls:"):
        action_tls_wrapper(args)
        return


if __name__ == "__main__":
    main()
