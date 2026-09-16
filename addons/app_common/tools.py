# -*- coding: utf-8 -*-
from odoo.http import request

import requests
import base64
from io import BytesIO
import uuid

def get_image_from_url(url):
    if not url:
        return None
    try:
        response = requests.get(url, timeout=5)
    except Exception as e:
        return None
    # 返回这个图片的base64编码
    return base64.b64encode(BytesIO(response.content).read())


def get_image_url2attachment(url):
    if not url:
        return None
    try:
        if url.startswith('//'):
            url = 'https:%s' % url
        response = requests.get(url, timeout=90)
    except Exception as e:
        return None, None
    # 返回这个图片的base64编码
    image = base64.b64encode(BytesIO(response.content).read())
    file_name = url.split('/')[-1]
    return image, file_name


def get_image_base642attachment(data):
    if not data:
        return None
    try:
        image_data = data.split(',')[1]
        file_name = str(uuid.uuid4()) + '.png'
        return image_data, file_name
    except Exception as e:
        return None, None

def get_ua_type(self):
    ua = request.httprequest.headers.get('User-Agent')
    # 临时用 agent 处理，后续要前端中正确处理或者都从后台来
    # 微信浏览器
    #  MicroMessenger: Mozilla/5.0 (Linux; Android 10; ELE-AL00 Build/HUAWEIELE-AL00; wv)
    # AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120
    # MQQBrowser/6.2 TBS/045525 Mobile Safari/537.36 MMWEBID/3135 MicroMessenger/8.0.2.1860(0x2800023B) Process/tools WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64
    # 微信浏览器，开发工具，网页 iphone
    # ,Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1
    # wechatdevtools/1.03.2011120 MicroMessenger/7.0.4 Language/zh_CN webview/16178807094901773
    # webdebugger port/27772 token/b91f4a234b918f4e2a5d1a835a09c31e

    # 微信小程序
    # MicroMessenger: Mozilla/5.0 (Linux; Android 10; ELE-AL00 Build/HUAWEIELE-AL00; wv)
    # AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.62 XWEB/2767 MMWEBSDK/20210302 Mobile Safari/537.36 MMWEBID/6689 MicroMessenger/8.0.2.1860(0x2800023B) Process/appbrand2 WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64
    # MiniProgramEnv/android
    # 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_7_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.37(0x18002529) NetType/WIFI Language/zh_CN'
    # 微信浏览器，开发工具，小程序，iphone
    # Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1
    # wechatdevtools/1.03.2011120 MicroMessenger/7.0.4 Language/zh_CN webview/
    # 微信内，iphone web
    # Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148
    # MicroMessenger/8.0.3(0x1800032a) NetType/WIFI Language/zh_CN
    # 安卓app,h5
    # ELE-AL00(Android/10) (cn.erpapp.o20sticks.App/13.20.12.09) Weex/0.26.0 1080x2265

    # web 表示普通浏览器，后续更深入处理
    utype = 'web'
    # todo: 引入现成 py lib，处理企业微信
    if 'MicroMessenger' in ua and 'webdebugger' not in ua \
        and ('miniProgram' in ua or 'MiniProgram' in ua or 'MiniProgramEnv' in ua or 'wechatdevtools' in ua):
        # 微信小程序及开发者工具
        utype = 'wxapp'
    elif 'wxwork' in ua:
        utype = 'qwapp'
    elif 'MicroMessenger' in ua:
        # 微信浏览器
        utype = 'wxweb'
    elif 'cn.erpapp.o20sticks.App' in ua:
        # 安卓app
        utype = 'native_android'
    elif 'BytedanceWebview' in ua:
        utype = 'dyweb'
    # _logger.warning('=========get ua %s,%s' % (utype, ua))
    return utype
