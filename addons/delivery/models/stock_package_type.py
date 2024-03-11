# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PackageType(models.Model):
    _inherit = 'stock.package.type'

    shipper_package_code = fields.Char('Carrier Code')
    package_carrier_type = fields.Selection([('none', 'No carrier integration')], string='Carrier', default='none')

    @api.onchange('package_carrier_type')
    def _onchange_carrier_type(self):
        carrier_id = self.env['delivery.carrier'].search([('delivery_type', '=', self.package_carrier_type)], limit=1)
        if carrier_id:
            self.shipper_package_code = carrier_id._get_default_custom_package_code()
        else:
            self.shipper_package_code = False
