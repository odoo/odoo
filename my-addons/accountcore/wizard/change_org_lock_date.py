# -*- coding: utf-8 -*-
from odoo import api
from odoo import exceptions
from odoo import fields
from odoo import models
from odoo.addons.accountcore.models.ac_obj import ACTools
# 改变记账状态向导s


class change_steps(models.TransientModel):
    '''改变机构/主体锁定日期向导'''
    _name = 'accountcore.org_change_lock_date'
    _description = '改变机构/主体锁定日期向导'
    lock_date = fields.Date(string="锁定日期")

    @ACTools.refuse_role_search
    def do(self):
        '''批量机构/主体锁定日期'''
        lock_date = self.lock_date
        orgs = self.env['accountcore.org'].sudo().browse(
            self._context.get('active_ids'))
        orgs.write({"lock_date":lock_date})