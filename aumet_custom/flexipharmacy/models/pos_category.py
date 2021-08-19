# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo.exceptions import Warning
from odoo import models, fields, api, _


class PosCategory(models.Model):
    _inherit = 'pos.category'

    @api.constrains('pos_category_comm_ids', 'pos_category_comm_ids.commission')
    def _check_commission_values(self):
        if self.pos_category_comm_ids.filtered(
                lambda line: line.calculation == 'percentage' and line.commission > 100 or line.commission < 0.0):
            raise Warning(_('Commission value for Percentage type must be between 0 to 100.'))

    pos_category_comm_ids = fields.One2many('pos.category.commission', 'category_id', string="Doctor Commission")


class PosCategoryCommission(models.Model):
    _name = 'pos.category.commission'
    _description = "Point of Sale Category Commission"

    doctor_id = fields.Many2one('res.partner', string='Doctor', domain="[('is_doctor', '=', True)]")
    calculation = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed_price', 'Fixed Price')
    ], string='Calculation')
    commission = fields.Float(string='Commission')
    category_id = fields.Many2one('pos.category')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
