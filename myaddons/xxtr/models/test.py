#-*- encoding:utf-8 -*-
import requests
import re
import time
import random
import datetime

def get_response(wj_url):
    """
    访问问卷网页，获取网页代码
    :return: get请求返回的response
    """
    ip = '{}.{}.{}.{}'.format(112, random.randint(64, 68), random.randint(0, 255), random.randint(0, 255))
    header = {
        'X-Forwarded-For': ip,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko\
                        ) Chrome/71.0.3578.98 Safari/537.36',
    }
    response = requests.get(url=wj_url, headers=header)
    cookie = response.cookies
    print(response)
    return response


if __name__ == '__main__':
    # w = get_response('https://www.wjx.cn/m/101612165.aspx')
    # print(w.text)
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) )
    time_stamp = '{}{}'.format(int(time.time()), random.randint(100, 200))
    print(time_stamp)