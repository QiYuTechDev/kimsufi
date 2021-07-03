import sys
from pprint import pprint
from typing import List, Optional

import click
import requests
from pydantic import BaseModel, Field

url = "https://www.ovh.com/engine/api/dedicated/server/availabilities?country=ie"

headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0",
    "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
}


class DataCenter(BaseModel):
    availability: str = Field(..., title="是否有货")
    datacenter: str = Field(..., title="数据中心")


class Region(BaseModel):
    region: str = Field(..., title="地区")
    hardware: str = Field(..., title="型号")
    datacenters: Optional[List[DataCenter]] = Field(None, title="数据中心列表")


def filter_by_dc(r: Region, dc: str) -> Optional[Region]:
    if r.datacenters is None or len(r.datacenters) == 0:
        return None

    dc_list = r.datacenters

    ret_dc_list = list(filter(lambda x: x.datacenter == dc, dc_list))
    if len(ret_dc_list) == 0:
        return None

    r.datacenters = ret_dc_list
    return r


def filter_by_availability(r: Region) -> Optional[Region]:
    if r.datacenters is None or len(r.datacenters) == 0:
        return None

    dc_list = r.datacenters

    ret_dc_list = list(
        filter(lambda x: x.availability.lower() != "unavailable", dc_list)
    )
    if len(ret_dc_list) == 0:
        return None
    r.datacenters = ret_dc_list
    return r


@click.command()
@click.option("--region", help="过滤 region [不设置则默认所有都可以]")
@click.option("--hardware", help="过滤 硬件型号 [不设置则默认所有都可以]")
@click.option("--datacenter", help="过滤 数据中心 [不设置则默认所有都可以]")
@click.option("--webhook", help="监控通知地址 [不设置则默认不通知, 发送 POST 通知]")
def main(
    region: Optional[str],
    hardware: Optional[str],
    datacenter: Optional[str],
    webhook: Optional[str],
):
    """
    kimsufi 库存监控

    Model   hardware
    KS-3    1801sk14
    KS-7    1801sk18
    KS-10   1801sk21

    KS-12   1804sk23

    看起来 KS 系列对应的:
    1084 是 northAmerica 区域
    1801 是 europe 区域
    """
    print(f"{region=} {hardware=} {datacenter=}")
    resp = requests.get(url, headers=headers)
    data_list = resp.json()
    ret_list: List[Region] = list(map(lambda x: Region(**x), data_list))

    if region is not None:
        ret_list = list(filter(lambda x: x.region == region, ret_list))

    if hardware is not None:
        ret_list = list(filter(lambda x: x.hardware == hardware, ret_list))

    if datacenter is not None:
        ret_list = list(
            filter(
                lambda x: x is not None,
                map(lambda r: filter_by_dc(r, datacenter), ret_list),
            )
        )

    ret_list = list(
        filter(
            lambda x: x is not None, map(lambda r: filter_by_availability(r), ret_list)
        )
    )

    json_list = list(map(lambda x: x.dict(), ret_list))

    if webhook and len(json_list) > 0:  # 保证有数据再调用 WebHook
        resp = requests.post(webhook, json=json_list)
        if not resp.ok:
            print(f"发送 WebHook 请求失败")
            sys.exit(2)

    print("监控结果:")
    pprint(json_list, indent=2)


if __name__ == "__main__":
    main()
