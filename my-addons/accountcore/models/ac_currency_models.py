# -*- coding: utf-8 -*-
from odoo import models, fields, api, SUPERUSER_ID, exceptions


class AC_Currency(models.Model):
    '''币别'''
    _name = "accountcore.ac_currency"
    _description = '币别'
    number = fields.Char(string='币别编码', required=True)
    name = fields.Char(string="币名", required=True)
    exchange_rate = fields.Float(string="汇率", default=1, digits=(16, 6))
    glob_tag = fields.Many2many('accountcore.glob_tag',
                                string='全局标签',
                                index=True)
    _sql_constraints = [('accountcore_org_number_unique', 'unique(number)',
                         '币别编码重复了!'),
                        ('accountcore_org_name_unique', 'unique(name)',
                         '币别名称重复了!')]

    @api.depends('digit_capacity')
    def _get_digits(self):
        self.exchange_rate
