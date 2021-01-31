# -*- coding: utf-8 -*-
# 康虎软件工作室
# http://www.khcloud.net
# QQ: 360026606
# wechat: 360026606
#--------------------------

import logging
import re
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError


def is_valid_ip(ip):
    p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if p.match(ip):
        return True
    else:
        return False


class CFPrintServerUserMapping(models.Model):
    """
    康虎云报表用户与打印服务器映射
    """
    _name = 'cf.print.server.user.mapping'
    _description = _("Print Server and User Mapping")

    @api.model
    def _current_user_domain(self):
        return [('id', '=', self.env.user.id)]

    user_id = fields.Many2one("res.users", string="用户", default=lambda self: self.env.user.id, domain=_current_user_domain, help="关联的用户")
    prn_server_ip = fields.Char(string="打印服务器IP", help="当前用户使用的打印服务器的IP地址。如果不需要发送到别的电脑上打印，请勿修改！")
    prn_server_port = fields.Integer(string="打印服务器端口", default=54321, help="当前用户使用的打印服务器的监听端口。如果不需要发送到别的电脑上打印，请勿修改！")

    @api.model
    def create_or_show_print_svr_ip(self):
        mapping = self.search([('user_id.id','=',self.env.user.id)], limit=1)
        if not mapping:
            mapping = self.create({"prn_server_ip": "127.0.0.1", "prn_server_port": 54321})
        action = {
            'type': 'ir.actions.act_window',
            'name': _('打印服务器地址'),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'cf.print.server.user.mapping',
            'nodestroy': 'true',
            'res_id': mapping.id,
            'views': [(False, 'form')],
            'view_id': self.env.ref("cfprint.cf_print_server_mapping_form"),
            'target': 'new',
        }
        return action

    @api.model
    def create(self, vals):
        if vals.get("prn_server_ip", False):
            if not is_valid_ip(vals.get("prn_server_ip")):
                raise ValidationError(_("打印服务器的IP地址错误，请确认！"))
            if vals.get("prn_server_port", 0) <= 0 and vals.get("prn_server_port", 0)>=65535:
                vals["prn_server_port"] = 54321
            return super(CFPrintServerUserMapping, self).create(vals)
        return False

    def write(self, vals):
        if vals.get("prn_server_ip", False):
            if not is_valid_ip(vals.get("prn_server_ip")):
                raise ValidationError(_("打印服务器的IP地址错误，请确认！"))
        if vals.get("prn_server_port", False):
            if vals.get("prn_server_port", 0) <= 0 and vals.get("prn_server_port", 0)>=65535:
                vals["prn_server_port"] = 54321

        return super(CFPrintServerUserMapping, self).write(vals)
