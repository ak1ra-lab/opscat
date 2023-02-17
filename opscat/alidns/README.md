
# README for alidns.py

## 配置文件

可通过 `-c` 或 `--config` 选项指定配置文件位置, 在不指定此选项时, 默认读取 `~/.config/opscat/alidns/config.json` 文件, 默认位置配置文件不存在时还可以设置环境变量 `ACS_ACCESS_KEY`, `ACS_SECRET`, `ACS_REGION` 传递 `ak`, `secret`, `region` 值, 二者必须至少设置一种.

配置文件的格式为:

```json
{
    "ak": "xxxx",
    "secret": "xxxx",
    "region": "cn-hangzhou"
}
```

> [首页>新手上云指南>访问并使用云产品>地域和可用区](https://www.alibabacloud.com/help/zh/basics-for-beginners/latest/regions-and-zones)

## 基本用法

* 查询某域名下所有记录: `alidns -d example.com -a search`
* 查询符合特定关键词的 DNS 记录: `alidns -d example.com -a search --keyword api`

* 添加 DNS 记录: `alidns -d example.com -a add -t A -r alidns -v 1.1.1.1 -R "alidns A record add example"`
* 修改 DNS 记录: `alidns -d example.com -a update -t CNAME -r alidns -v alidns.example.com.cdn.dnsv1.com -R "alidns CNAME record update example"`
* 删除 DNS 记录: `alidns -d example.com -a delete -t CNAME -r alidns`

* 更多用法请执行: `alidns --help`

## 关于批量修改选项 `-b, --batch` 的说明

批量修改域名基本用法: `alidns -a batch -b batch-input.csv`

> `batch-input.csv` 文件格式请参考 [batch-input.example.csv](batch-input.example.csv) 文件

`-b, --batch` 选项同时支持读取标准输入, 即: `cat batch-input.csv | alidns -a batch -b -`

批量修改选项通过读取符合以下 headers 的 .csv 文件进行修改, 一行一条记录,
传入的 .csv 文件需要带上 headers 部分, 所要求的 headers 为:

`action,domain,type,record,line,value,priority,ttl,status,remark`

action 字段可用的选项为 `add`, `update` 和 `delete`,
不同类型的操作可以放在一个文件中输入, 比如下面这个例子一次性执行了 快速开始 中的三个操作:

```
action,domain,type,record,line,value,priority,ttl,status,remark
add,example.com,A,alidns,default,1.1.1.1,1,600,Enable,alidns A record add example
update,example.com,CNAME,alidns,default,alidns.example.com.cdn.dnsv1.com,1,600,Enable,alidns CNAME record update example
delete,example.com,CNAME,alidns,default,alidns.example.com.cdn.dnsv1.com,1,600,Enable,alidns CNAME record delete example
```

> 当然这里仅仅是作为例子演示, 实际上不会对同一条记录执行完 `add`, `update` 后立马 `delete` 的.

目前这里的 `line` 没有实际作用, 暂时没有[更新自定义线路](https://help.aliyun.com/document_detail/145060.html)的需求.

## 操作日志搜索功能

* 新增[获取域名操作日志](https://help.aliyun.com/document_detail/29756.html)的 action: `--action logs:domain`
* 新增[获取解析记录操作日志](https://help.aliyun.com/document_detail/29780.html)的 action: `--action logs:record`

实际在命令行操作中这两个 action 用处不大, 需要用到的时候都是直接在控制台操作了.
