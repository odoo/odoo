# -*- coding: utf-8 -*-
from odoo import api
from odoo import exceptions
from odoo import fields
from odoo import models
from odoo.addons.accountcore.models.ac_obj import ACTools
# 改变记账状态向导s


class change_class(models.TransientModel):
    '''改变机构/主体组名向导'''
    _name = 'accountcore.org_change_class'
    _description = '改变机构/主体组名向导'
    org_class = fields.Char(string="机构组名")

    @ACTools.refuse_role_search
    def do(self):
        '''批量机构/主体组名'''
        org_class = self.org_class
        orgs = self.env['accountcore.org'].sudo().browse(
            self._context.get('active_ids'))
        orgs.write({"org_class": org_class})
