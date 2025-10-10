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
from ..lib.user_agents import parse

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
    
    @api.model
    def _app_dt2local(self, dt_value, return_format=False):
        """
        将带时区的日期时间转换为当前用户 env 时区并格式化为字符串
        :param dt_value: 输入的日期时间（没时区时默认UTC，来自数据库）
        :param format_str: 输出格式字符串，如 '%Y-%m-%d %H:%M:%S，默认用 env.lang 的设置
        :return: 指定用户时区下的格式化时间字符串
        """
        if not dt_value:
            return dt_value
        # 处理默认格式
        if not return_format:
            lang_obj = self.env.ref('base.lang_zh_CN')
            lang_ref = 'base.lang_%s' % self.env.lang
            try:
                lang_obj = self.env.ref(lang_ref)
            except Exception as e:
                pass
            return_format = '%s %s' % (lang_obj.date_format, lang_obj.time_format)

        # 用户时区，默认中国
        local_tz = pytz.timezone(self.env.user.tz or 'Etc/GMT-8')
        
        # 如果输入是字符串，先解析为datetime对象, 假设输入是标准的数据库时间格式
        if isinstance(dt_value, str):
            dt_value = datetime.strptime(dt_value, return_format)
            
        # 设置原始时区为UTC（PostgreSQL数据库通常存储UTC时间）
        if dt_value.tzinfo is None:
            dt_value = pytz.utc.localize(dt_value)
        
        local_dt = dt_value.astimezone(local_tz)
        return local_dt.strftime(return_format)
    
    @api.model
    def _app_dt2utc(self, dt_value, return_format=False):
        """
        将带时区的日期时间转换为标准 utc 时间，并格式化为字符串
        :param dt_value: 输入的日期时间（没时区时默认用户时区，来自数据库）
        :param format_str: 输出格式字符串，如 '%Y-%m-%d %H:%M:%S，默认用 env.lang 的设置
        :return: 指定用户时区下的格式化时间字符串
        """
        if not dt_value:
            return dt_value
        # 处理默认格式
        if not return_format:
            lang_obj = self.env.ref('base.lang_zh_CN')
            lang_ref = 'base.lang_%s' % self.env.lang
            try:
                lang_obj = self.env.ref(lang_ref)
            except Exception as e:
                pass
            return_format = '%s %s' % (lang_obj.date_format, lang_obj.time_format)

        # 用户时区，默认中国
        local_tz = pytz.timezone(self.env.user.tz or 'Etc/GMT-8')
        
        # 如果输入是字符串，先解析为datetime对象, 假设输入是标准的数据库时间格式, 时区为默认用户时区
        if isinstance(dt_value, str):
            dt_value = datetime.strptime(dt_value, return_format)
            
        # 设置原始时区为用户时区（PostgreSQL数据库通常存储UTC时间）
        if dt_value.tzinfo is None:
            dt_value = local_tz.localize(dt_value)
        
        utc_dt = dt_value.replace(tzinfo=pytz.timezone('UTC'))
        return utc_dt.strftime(return_format)

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
    
    @api.model
    def get_ua_type(self):
        return get_ua_type()
    
    @api.model
    def deep_merge(self, a, b):
        # todo: 此处只处理2级，后续如需更深级别可以使用第三方库
        # from deepmerge import always_merger
        return deep_merge(a, b)

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
    ua_parse = str(parse(ua))
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
    elif 'Chrome Mobile' in ua_parse or 'Mobile Safari' in ua_parse:
    #     增加移动端 web
        utype = 'mweb'
    # _logger.warning('=========get ua %s,%s' % (utype, ua))
    return utype
def deep_merge(a, b):
    """
    深度合并两个二级 dict，对数值进行叠加，以b为主。
    如果 a 和 b 有相同的键，则对它们的值进行合并；
    如果值是 dict，则递归处理；
    否则将 b 的值更新至 a 上。
    """
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                deep_merge(a[key], b[key])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a
