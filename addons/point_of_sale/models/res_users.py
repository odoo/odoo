# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    pos_security_pin = fields.Char(string='Security PIN', size=32, help='A Security PIN used to protect sensible functionality in the Point of Sale')

    group_point_of_sale_user = fields.Selection(
        selection=lambda self: self._get_group_selection('base.module_category_point_of_sale'),
        string='Point of Sale', compute='_compute_groups_id', inverse='_inverse_groups_id',
        category_xml_id='base.module_category_point_of_sale')

    @api.constrains('pos_security_pin')
    def _check_pin(self):
        if self.pos_security_pin and not self.pos_security_pin.isdigit():
            raise UserError(_("Security PIN can only contain digits"))
