# -*- coding: utf-8 -*-
# 康虎软件工作室
# http://www.khcloud.net
# QQ: 360026606
# wechat: 360026606
#--------------------------
####################################################
#  康虎云报表模板存储
#  该表中以Base64格式存储康虎云报表，可以方便地取
#  出来嵌入到康虎云报表打印数据(json)中
#
####################################################

import logging
import base64
from odoo import http, _
from odoo.http import request
from io import StringIO
# from werkzeug.utils import redirect

_logger = logging.getLogger(__name__)

class CFPrintController(http.Controller):
    """
    康虎云报表模板Controller类
    """
    @http.route('/cfprint/template', type='http', auth='public')  #auth='user'
    def get_cfprint_template(self, templ_id):
        """
        康虎云报表模板下载
        :param templ_id:    模板唯一ID
        :return:
        """
        template = request.env['cf.template'].sudo().search_read( [('templ_id', '=', templ_id)])
        if template:
            template = template[0]
            data = StringIO(base64.standard_b64decode(template["template"]))
            return http.send_file(data, filename=template['templ_id']+'.fr3', as_attachment=True)
        else:
            return request.not_found()