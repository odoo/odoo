# -*- coding: utf-8 -*-

import base64
from io import BytesIO
import requests
from math import radians, cos, sin, asin, sqrt

from ..lib.user_agents import parse
from ..models.base import get_ua_type


from odoo import api, http, SUPERUSER_ID, _
from odoo import http, exceptions
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

class AppController(http.Controller):

    def get_image_from_url(self, url):
        if not url:
            return None
        try:
            response = requests.get(url)  # 将这个图片保存在内存
        except Exception as e:
            return None
        # 返回这个图片的base64编码
        return base64.b64encode(BytesIO(response.content).read())

    @http.route(['/my/ua'], auth='public', methods=['GET'], sitemap=False)
    def app_ua_show(self):
        # https://github.com/selwin/python-user-agents
        ua_string = request.httprequest.headers.get('User-Agent')
        user_agent = parse(ua_string)
        ua_type = get_ua_type()
        ustr = "Request UA: <br/> %s <br/>Parse UA: <br/>%s <br/>UA Type:<br/>%s <br/>" % (ua_string, str(user_agent), ua_type)
        return request.make_response(ustr, [('Content-Type', 'text/html')])
        
    def get_ua_type(self):
        return get_ua_type()

def haversine(lon1, lat1, lon2, lat2):
    # 计算地图上两点的距离
    # in:经度1，纬度1，经度2，纬度2 （十进制度数）
    # out: 距离（米）
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # 将十进制度数转化为弧度
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # haversine公式
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # 地球平均半径，单位为公里
    return c * r * 1000
