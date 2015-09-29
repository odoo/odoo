# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
from openerp.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    pos_security_pin = fields.Char(string='Security PIN', size=32, help='A Security PIN used to protect sensible functionality in the Point of Sale')
    pos_config = fields.Many2one('pos.config', string='Default Point of Sale', domain=[('state', '=', 'active')])

    @api.constrains('pos_security_pin')
    def _check_pin(self):
        if self.pos_security_pin and not self.pos_security_pin.isdigit():
            raise UserError(_("Security PIN can only contain digits"))
