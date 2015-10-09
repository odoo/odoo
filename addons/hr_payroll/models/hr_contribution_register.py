#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContribRegister(models.Model):
    '''
    Contribution Register
    '''

    _name = 'hr.contribution.register'
    _description = 'Contribution Register'

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one('res.partner', 'Partner')
    name = fields.Char(required=True)
    register_line_ids = fields.One2many('hr.payslip.line', 'register_id', 'Register Line', readonly=True)
    note = fields.Text('Description')
