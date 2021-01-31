# -*- coding: utf-8 -*-
from odoo import models, fields
# 继承和扩展model-开始
# 扩展基础用户属性
class ExtensionUser(models.Model):
    '''扩展基础用户属性'''
    _inherit = 'res.users'
    currentOrg = fields.Many2one('accountcore.org', string="当前机构/主体")
    voucherNumberTastics = fields.Many2one('accountcore.voucher_number_tastics',
                                           string='默认凭证编号策略')
    current_date = fields.Date(
        string='当期操作日期', default=fields.Date.today())
    current_itemclass = fields.Many2one('accountcore.itemclass', string="当前核算项目类别")
# 继承和扩展model-结束
# model-结束