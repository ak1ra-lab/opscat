#! /usr/bin/env python3
# coding: utf-8
# author: ak1ra
# date: 2021-10-13
# a helper script to search/add/update/delete aliyun DNS records

import io
import os
import re
import sys
import json
import datetime
import argparse

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import AcsRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainsRequest import DescribeDomainsRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordInfoRequest import DescribeDomainRecordInfoRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainLogsRequest import DescribeDomainLogsRequest
from aliyunsdkalidns.request.v20150109.DescribeRecordLogsRequest import DescribeRecordLogsRequest
from aliyunsdkalidns.request.v20150109.AddDomainRecordRequest import AddDomainRecordRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRemarkRequest import UpdateDomainRecordRemarkRequest
from aliyunsdkalidns.request.v20150109.DeleteDomainRecordRequest import DeleteDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DeleteSubDomainRecordsRequest import DeleteSubDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.SetDomainRecordStatusRequest import SetDomainRecordStatusRequest


def print_json(json_obj):
    if isinstance(json_obj, str):
        print(json.dumps(json.loads(json_obj), ensure_ascii=False, indent=4))
    else:
        print(json.dumps(json_obj, ensure_ascii=False, indent=4))


def save_json(filename, data, mode='w', encoding="utf-8"):
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    if isinstance(data, str):
        data = json.loads(data)
    with open(filename, mode, encoding=encoding) as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=4))


def print_kv_list_results(results, results_type="records",
                          sep="\t", results_break="=", results_break_len=120):
    if results_type == "records":
        headers = ["RecordId", "Type", "RR",
                   "Value", "TTL", "Status", "Remark"]
    if results_type == "logs":
        headers = ["ActionTime", "Action", "Message"]
    results_joined = [sep.join(headers)]
    for result in results:
        results_joined.append(
            sep.join(str(result.get(header)) for header in headers)
        )

    print("\n".join(results_joined))
    print(results_break * results_break_len)


def read_input(prompt, default=""):
    try:
        choice = input(prompt)
    except EOFError:
        choice = default
    return choice.strip()


def csv_to_kv_list(csv_file, headers=[], sep=","):
    if isinstance(csv_file, io.TextIOWrapper):
        # argparse.FileType: io.TextIOWrapper 已经是一个 open 状态的文件
        with csv_file as f:
            csv_lines = [line.strip()
                         for line in f.readlines() if line.strip()]
    else:
        with open(csv_file, encoding="utf-8") as f:
            csv_lines = [line.strip()
                         for line in f.readlines() if line.strip()]

    if not headers:
        headers = [header.strip() for header in csv_lines.pop(0).split(sep)]
    else:
        csv_lines.pop(0)

    csv_kv_list = []
    for csv_line in csv_lines:
        item_list = [item.strip() for item in csv_line.split(sep)]
        csv_kv_list.append(
            {key: value for key, value in zip(headers, item_list)}
        )

    return csv_kv_list


def init_client(config_file):
    try:
        with open(os.path.expanduser(config_file), encoding="utf-8") as f:
            config = json.loads(f.read())
    except IOError:
            config = {}
    ak = os.environ.get("ACS_ACCESS_KEY") or config.get("ak")
    secret = os.environ.get("ACS_SECRET") or config.get("secret")
    region = os.environ.get("ACS_REGION") or config.get("region")
    return AcsClient(ak, secret, region)


def paging_request(client: AcsClient, req: AcsRequest):
    resp_list = []
    page_number = 1
    total_count = sys.maxsize
    while (page_number * req.get_PageSize()) <= total_count:
        req.set_PageNumber(page_number)
        resp = client.do_action_with_exception(req)
        resp_json = json.loads(resp.decode())
        total_count = resp_json.get("TotalCount")
        page_number += 1
        resp_list.append(resp_json)
    return resp_list


# 对 aliyunsdkalidns.request.v*.*Request 方法的封装
def get_domains(client: AcsClient, page_size=100):
    req = DescribeDomainsRequest()
    req.set_PageSize(page_size)
    domains = []
    for resp in paging_request(client, req):
        domains.extend(resp.get("Domains").get("Domain"))

    return domains


def get_domain_logs(client: AcsClient, start_date, end_date=None, page_size=100):
    req = DescribeDomainLogsRequest()
    req.set_StartDate(start_date)
    if end_date:
        req.set_endDate(end_date)
    req.set_PageSize(page_size)
    domain_logs = []
    for resp in paging_request(client, req):
        domain_logs.extend(resp.get("DomainLogs").get("DomainLog"))

    return domain_logs


def get_record_logs(client: AcsClient, domain, start_date, end_date=None, page_size=100):
    req = DescribeRecordLogsRequest()
    req.set_DomainName(domain)
    req.set_StartDate(start_date)
    if end_date:
        req.set_endDate(end_date)
    req.set_PageSize(page_size)
    record_logs = []
    for resp in paging_request(client, req):
        record_logs.extend(resp.get("RecordLogs").get("RecordLog"))

    return record_logs


def get_domain_records(client: AcsClient, domain, mode="LIKE",
                       keyword="", rr_keyword="", type_keyword="", value_keyword="", page_size=100):
    req = DescribeDomainRecordsRequest()

    if keyword:
        req.set_KeyWord(keyword)
    if rr_keyword:
        mode = "ADVANCED"
        req.set_RRKeyWord(rr_keyword)
    if type_keyword:
        mode = "ADVANCED"
        req.set_TypeKeyWord(type_keyword)
    if value_keyword:
        mode = "ADVANCED"
        req.set_ValueKeyWord(value_keyword)
    req.set_DomainName(domain)
    req.set_PageSize(page_size)
    req.set_SearchMode(mode)

    records = []
    for resp in paging_request(client, req):
        records.extend(resp.get("DomainRecords").get("Record"))

    return records


def get_domain_record_info(client: AcsClient, record_id):
    req = DescribeDomainRecordInfoRequest()
    req.set_RecordId(record_id)
    resp = client.do_action_with_exception(req)
    return json.loads(resp.decode())


def add_domain_record(client: AcsClient, domain,
                      resolv_type, resolv_record, value, ttl=600, priority=1):
    req = AddDomainRecordRequest()
    req.set_DomainName(domain)
    req.set_RR(resolv_record)
    req.set_Type(resolv_type)
    req.set_Value(value)
    req.set_TTL(ttl)
    if resolv_type == "MX":
        req.set_Priority(priority)
    resp = client.do_action_with_exception(req)
    record_id = json.loads(resp.decode()).get("RecordId")
    return record_id


def update_domain_record(client: AcsClient, record_id,
                         resolv_type, resolv_record, value, ttl=600, priority=1):
    # https://help.aliyun.com/document_detail/29774.html
    req = UpdateDomainRecordRequest()
    req.set_RecordId(record_id)
    req.set_RR(resolv_record)
    req.set_Type(resolv_type)
    if value:
        req.set_Value(value)
    if ttl:
        req.set_TTL(ttl)
    if resolv_type == "MX":
        req.set_Priority(priority)
    resp = client.do_action_with_exception(req)
    return json.loads(resp.decode())


def update_domain_record_remark(client: AcsClient, record_id, remark=""):
    # https://help.aliyun.com/document_detail/143569.html
    req = UpdateDomainRecordRemarkRequest()
    # Error:InvalidRemark.Format 50 characters long,
    # It can only contain numbers,Chinese,English and special characters: _ - , . ，。
    remark_pattern = re.compile(r"[\u4e00-\u9fa5，。a-zA-Z0-9_,.-]+")
    remark_strip = "".join(re.findall(remark_pattern, remark))[:50]

    req.set_RecordId(record_id)
    req.set_Remark(remark_strip)
    resp = client.do_action_with_exception(req)
    return json.loads(resp.decode())


def delete_domain_record(client: AcsClient, record_id):
    req = DeleteDomainRecordRequest()
    req.set_RecordId(record_id)
    resp = client.do_action_with_exception(req)
    return json.loads(resp.decode())


def delete_subdomain_records(client: AcsClient, domain, resolv_type, resolv_record):
    # 这个方法太危险了! 尽量避免调用这个函数
    req = DeleteSubDomainRecordsRequest()
    req.set_DomainName(domain)
    req.set_RR(resolv_record)
    req.set_Type(resolv_type)
    resp = client.do_action_with_exception(req)
    return json.loads(resp.decode())


def set_domain_record_status(client: AcsClient, record_id, status="Enable"):
    req = SetDomainRecordStatusRequest()
    req.set_RecordId(record_id)
    req.set_Status(status)
    resp = client.do_action_with_exception(req)
    return json.loads(resp.decode())


# 以下函数为对上述封装函数的组合调用
def get_record_id_by_record(client: AcsClient, **kwargs):
    if not kwargs.get("record_id"):
        keyword = kwargs.get("record")
        records = get_domain_records(
            client=client,
            domain=kwargs.get("domain"),
            mode="EXACT",
            keyword=keyword
        )
        if len(records) <= 0:
            return
        if len(records) > 1:
            print_kv_list_results(records, results_type="records")
            record_id = read_input(
                prompt="按 RR:%s 条件查询到多条记录, 请输入需要执行 %s 操作的 RecordId: "
                % (keyword, kwargs.get("action"))
            )
        else:
            record_id = records[0].get("RecordId")
    else:
        record_id = kwargs.get("record_id")

    return record_id


def add_domain_record_with_remark(client: AcsClient, **kwargs):
    record_id = add_domain_record(
        client=client,
        domain=kwargs.get("domain"),
        resolv_type=kwargs.get("type"),
        resolv_record=kwargs.get("record"),
        value=kwargs.get("value"),
        ttl=kwargs.get("ttl"),
        priority=kwargs.get("priority")
    )
    update_domain_record_remark(client, record_id, kwargs.get("remark"))
    if kwargs.get("status").lower() in ["disable", "暂停"]:
        set_domain_record_status(client, record_id, kwargs.get("status"))
    return record_id


def update_domain_record_with_remark(client: AcsClient, **kwargs):
    record_id = get_record_id_by_record(client, **kwargs)
    if not record_id:
        return
    # 根据 record_id 获取现有值, 避免每次都需要传递完整参数
    record = get_domain_record_info(client, record_id)

    # 传入 UpdateDomainRecord 接口的参数完全一致时会出现 Error:DomainRecordDuplicate, 此时需避免调用
    resolv_record = kwargs.get("record") or record.get("RR")
    resolv_type = kwargs.get("type") or record.get("Type")
    value = kwargs.get("value") or record.get("Value")
    # argparse 有设置 int 类型的默认值, csv 文件转 kwargs 后对应 key 是存在的
    # 若源 csv 文件没有为对应列设置值, kwargs.get() 类型应该也是 str 类型的空字符串,
    # kwargs.get() 只有 key 不存在时会获取到 None, 但是 "" 不能转 int
    # DescribeDomainRecordInfo 返回的结果中 TTL, Priority 字段类型为 int
    ttl = str(kwargs.get("ttl")) or str(record.get("TTL"))
    priority = str(kwargs.get("priority")) or str(record.get("Priority"))
    remark = kwargs.get("remark") or record.get("Remark")
    status = kwargs.get("status") or record.get("Status")
    record_info_eq = [
        resolv_record == record.get("RR"),
        resolv_type == record.get("Type"),
        value == record.get("Value"),
        ttl == str(record.get("TTL"))
    ]
    if resolv_type == "MX":
        record_info_eq.append(priority == str(record.get("Priority")))

    print("子域名更新前记录信息:")
    print_kv_list_results([record], results_type="records")
    if not all(record_info_eq):
        update_domain_record(client, record_id, resolv_type,
                             resolv_record, value, ttl, priority)
    if remark != record.get("Remark"):
        update_domain_record_remark(client, record_id, remark)
    if status.lower() != record.get("Status").lower():
        if status.lower() in ["enable", "启用", "正常"]:
            set_domain_record_status(client, record_id, "Enable")
        else:
            set_domain_record_status(client, record_id, "Disable")

    print("子域名更新后记录信息:")
    print_kv_list_results([get_domain_record_info(
        client, record_id)], results_type="records")

    return record_id


def delete_domain_record_by_delete_type(client: AcsClient, delete_type="id", **kwargs):
    if delete_type == "subdomain":
        records = get_domain_records(
            client=client,
            domain=kwargs.get("domain"),
            mode="ADVANCED",
            rr_keyword=kwargs.get("record"),
            type_keyword=kwargs.get("type")
        )
        if len(records) <= 0:
            return
        print_kv_list_results(records, results_type="records")
        choice = read_input(
            prompt="确认按 (Type:%s, RR:%s) 条件查询并删除所有解析记录? [y/N]: "
            % (kwargs.get("type"), kwargs.get("record")),
            default="N"
        )
        if choice.lower() == "y" or choice.lower() == "yes":
            delete_subdomain_records(
                client=client,
                domain=kwargs.get("domain"),
                resolv_type=kwargs.get("type"),
                resolv_record=kwargs.get("record")
            )
    else:
        record_id = get_record_id_by_record(client, **kwargs)
        if record_id:
            delete_domain_record(client, record_id)


def add_update_delete(client: AcsClient, **kwargs):
    action = kwargs.get("action", "")

    # add
    if action == "add":
        add_domain_record_with_remark(client, **kwargs)

    # update
    if action == "update":
        update_domain_record_with_remark(client, **kwargs)

    # delete, delete:subdomain
    if action.startswith("delete"):
        if action.endswith(":subdomain"):
            delete_type = "subdomain"
        else:
            delete_type = "id"
        delete_domain_record_by_delete_type(client, delete_type, **kwargs)


def parse_args():
    parser = argparse.ArgumentParser()
    action_choices = (
        "batch", "search", "search:exact", "logs:domain", "logs:record",
        "add", "update", "delete", "delete:subdomain"
    )
    type_choices = (
        "A", "NS", "MX", "TXT", "CNAME",
        "SRV", "AAAA", "CAA", "REDIRECT_URL", "FORWARD_URL"
    )
    config_default = "~/.config/opscat/alidns/config.json"
    start_date_default = datetime.timedelta(days=30)

    parser.add_argument("-c", "--config", default=config_default,
                        help="保存 ak, secret, region 值的配置文件, 默认值 %s" % config_default)
    parser.add_argument("-b", "--batch", type=argparse.FileType("r", encoding="utf-8"),
                        help="执行批量 add/update/delete 动作的 .csv 文件输入, 可使用 - 读取标准输入")

    parser.add_argument("-a", "--action", choices=action_choices, default="search",
                        help="执行本脚本的动作, 默认值为 search")
    parser.add_argument("-d", "--domain", help="域名操作对象, 如 example.com")
    parser.add_argument("-k", "--keyword", help="执行 search 动作时的关键字")
    parser.add_argument("-t", "--type", choices=type_choices,
                        help="执行 add/update 动作时的记录类型, see: https://tg.pe/G9u")
    parser.add_argument("-r", "--record", help="执行 add/update/delete 动作时的主机记录")
    parser.add_argument("-v", "--value", help="执行 add/update 动作时的记录值")
    parser.add_argument("-R", "--remark", help="执行 add/update 动作时的备注")
    parser.add_argument("-s", "--status", default="Enable",
                        help="执行 add/update 动作时的域名状态")
    parser.add_argument("-T", "--ttl", type=int, default=600,
                        help="解析生效时间, 默认为 600 秒(10 分钟)")
    parser.add_argument("-P", "--priority", type=int, default=1,
                        help="MX 记录的优先级, 范围 [1, 50]. 记录类型为 MX 时此参数必须, 数值越低, 优先级越高.")

    parser.add_argument("-S", "--start-date",
                        default=(datetime.date.today() -
                                 start_date_default).strftime("%Y-%m-%d"),
                        help="执行日志搜索时的起始日期(格式 YYYY-mm-dd, 默认值当前日期的 %d 天前)" % start_date_default.days)
    parser.add_argument("-E", "--end-date", help="执行日志搜索时的截止日期(格式 YYYY-mm-dd)")

    parser.add_argument("-I", "--record-id",
                        help="执行 update/delete 动作时的 recordID")

    return parser.parse_args()


def main():
    args = parse_args()
    client = init_client(args.config)

    # search, search:exact
    if args.action in ["search", "search:exact"]:
        mode = "EXACT" if args.action.endswith(":exact") else "LIKE"
        records = get_domain_records(
            client=client, domain=args.domain, mode=mode, keyword=args.keyword
        )
        print_kv_list_results(records, results_type="records")

    # logs:domain, logs:record
    if args.action == "logs:domain":
        domain_logs = get_domain_logs(client, args.start_date, args.end_date)
        print_kv_list_results(domain_logs, results_type="logs")

    if args.action == "logs:record":
        record_logs = get_record_logs(
            client, args.domain, args.start_date, args.end_date)
        print_kv_list_results(record_logs, results_type="logs")

    # action batch and -b, --batch
    if args.action == "batch":
        # .csv 输入文件的格式除了前两列增加了 action, domain 外,
        # 其余部分跟阿里云所要求的字段一致, 但此处把 header 关键字转成了英文方便后续使用
        batch_csv_headers = [
            "action", "domain", "type", "record", "line", "value", "priority", "ttl", "status", "remark"
        ]
        batch_kwargs = csv_to_kv_list(args.batch, batch_csv_headers)
    else:
        batch_kwargs = [args.__dict__]

    for kwargs in batch_kwargs:
        add_update_delete(client, **kwargs)


if __name__ == "__main__":
    main()
