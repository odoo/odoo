# -*- coding: utf-8 -*-

import requests
import base64
from io import BytesIO
import uuid
from PIL import Image
from datetime import date, datetime, time
import pytz

import logging

from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.http import request

_logger = logging.getLogger(__name__)

# 常规的排除的fields
EXCLU_FIELDS = [
    '__last_update',
    'access_token',
    'access_url',
    'access_warning',
    'activity_date_deadline',
    'activity_exception_decoration',
    'activity_exception_icon',
    'activity_ids',
    'activity_state',
    'activity_summary',
    'activity_type_id',
    'activity_user_id',
    'display_name',
    'message_attachment_count',
    'message_channel_ids',
    'message_follower_ids',
    'message_has_error',
    'message_has_error_counter',
    'message_has_sms_error',
    'message_ids',
    'message_is_follower',
    'message_main_attachment_id',
    'message_needaction',
    'message_needaction_counter',
    'message_partner_ids',
    'message_unread',
    'message_unread_counter',
    'website_message_ids',
    'write_date',
    'write_uid',
]


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _app_check_sys_op(self):
        if self.env.user.has_group('base.group_erp_manager'):
            return True
        return False

    @api.model
    def _get_normal_fields(self):
        f_list = []
        for k, v in self._fields.items():
            if k not in EXCLU_FIELDS:
                f_list.append(k)
        return f_list

    @api.model
    def _app_get_m2o_default(self, fieldname, domain=[]):
        if hasattr(self, fieldname) and self._fields[fieldname].type == 'many2one':
            if self._context.get(fieldname) or self._context.get('default_%s' % fieldname):
                return self._context.get(fieldname) or self._context.get('default_%s' % fieldname)
            else:
                if not domain:
                    domain = self._fields[fieldname].domain or []
                try:
                    rec = self.env[self._fields[fieldname].comodel_name].search(domain, limit=1)
                except Exception as e:
                    rec = self.env[self._fields[fieldname].comodel_name].search([], limit=1)
                return rec.id if rec else False
        return False

    def _app_dt2local(self, value, return_format=DEFAULT_SERVER_DATETIME_FORMAT):
        """
        将value中时间，按格式转为用户本地时间.注意只处理in str为字符串类型,如果是时间类型直接用 datetime.now(tz)
        """
        if not value:
            return value
        if isinstance(value, datetime):
            value = value.strftime(return_format)
        dt = datetime.strptime(value, return_format)
        user_tz = pytz.timezone(self.env.user.tz or 'Etc/GMT-8')
        _logger.warning('============= user2 tz: %s' % user_tz)
        dt = dt.replace(tzinfo=pytz.timezone('UTC'))
        return dt.astimezone(user_tz).strftime(return_format)

    def _app_dt2utc(self, value, return_format=DEFAULT_SERVER_DATETIME_FORMAT):
        """
        将value中用户本地时间，按格式转为UTC时间，输出 str
        """
        if not value:
            return value
        if isinstance(value, datetime):
            value = value.strftime(return_format)
        dt = datetime.strptime(value, return_format)
        pytz_timezone = pytz.timezone('Etc/GMT+8')
        dt = dt.replace(tzinfo=pytz.timezone('UTC'))
        return dt.astimezone(pytz_timezone).strftime(return_format)

    @api.model
    def _get_image_from_url(self, url):
        # 返回这个图片的base64编码
        if not self._app_check_sys_op():
            return False
        return get_image_from_url(url)

    @api.model
    def _get_image_url2attachment(self, url, mimetype_list=None):
        # Todo: mimetype filter
        if not self._app_check_sys_op():
            return False
        image, file_name = get_image_url2attachment(url)
        if image and file_name:
            try:
                attachment = self.env['ir.attachment'].create({
                    'datas': image,
                    'name': file_name,
                    'website_id': False,
                    'res_model': self._name,
                    'res_id': self.id,
                    'public': True,
                })
                attachment.generate_access_token()
                return attachment
            except Exception as e:
                _logger.error('get_image_url2attachment error: %s' % str(e))
                return False
        else:
            return False

    @api.model
    def _get_image_base642attachment(self, data):
        if not self._app_check_sys_op():
            return False
        image, file_name = get_image_base642attachment(data)
        if image and file_name:
            try:
                attachment = self.env['ir.attachment'].create({
                    'datas': image,
                    'name': file_name,
                    'website_id': False,
                    'res_model': self._name,
                    'res_id': self.id,
                    'public': True,
                })
                attachment.generate_access_token()
                return attachment
            except Exception as e:
                _logger.error('get_image_base642attachment error: %s' % str(e))
                return False
        else:
            return False
        
    @api.model
    def _get_video_url2attachment(self, url):
        if not self._app_check_sys_op():
            return False
        video, file_name = get_video_url2attachment(url)
        if video and file_name:
            try:
                attachment = self.env['ir.attachment'].create({
                    'datas': video,
                    'name': file_name,
                    'website_id': False,
                    'res_model': self._name,
                    'res_id': self.id,
                    'public': True,
                })
                attachment.generate_access_token()
                return attachment
            except Exception as e:
                _logger.error('get_video_url2attachment error: %s' % str(e))
                return False
        else:
            return False

    def get_ua_type(self):
        return get_ua_type()

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
        img = Image.open(BytesIO(base64.b64decode(image_data)))
        img = img.convert('RGB')
        output = BytesIO()
        img.save(output, format='JPEG')
        file_name = str(uuid.uuid4()) + '.jpeg'
        jpeg_data = output.getvalue()
        jpeg_base64 = base64.b64encode(jpeg_data)
        return jpeg_base64, file_name
    except Exception as e:
        return None, None
    
def get_video_url2attachment(url):
    if not url:
        return None
    try:
        if url.startswith('//'):
            url = 'https:%s' % url
        response = requests.get(url, timeout=90)
        video_content = response.content
    except Exception as e:
        return None, None
    # return this video in base64
    base64_video = base64.b64encode(video_content)
    file_name = url.split('/')[-1]
    return base64_video, file_name

def get_ua_type():
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
