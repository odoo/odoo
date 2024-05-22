# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'


    def _get_default_length_uom(self):
        # TODO master delete
        return self.env['product.template']._get_length_uom_name_from_ir_config_parameter()

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    height = fields.Integer('Height')
    width = fields.Integer('Width')
    packaging_length = fields.Integer('Length')
    max_weight = fields.Float('Max Weight', help='Maximum weight shippable in this packaging')
    shipper_package_code = fields.Char('Package Code')
    package_carrier_type = fields.Selection([('none', 'No carrier integration')], string='Carrier', default='none')
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name', default=_get_default_weight_uom)
    length_uom_name = fields.Char(string='Length unit of measure label', compute='_compute_length_uom_name')

    _sql_constraints = [
        ('positive_height', 'CHECK(height>=0)', 'Height must be positive'),
        ('positive_width', 'CHECK(width>=0)', 'Width must be positive'),
        ('positive_length', 'CHECK(packaging_length>=0)', 'Length must be positive'),
        ('positive_max_weight', 'CHECK(max_weight>=0.0)', 'Max Weight must be positive'),
    ]

    @api.onchange('package_carrier_type')
    def _onchange_carrier_type(self):
        carrier_id = self.env['delivery.carrier'].search([('delivery_type', '=', self.package_carrier_type)], limit=1)
        if carrier_id:
            self.shipper_package_code = carrier_id._get_default_custom_package_code()
        else:
            self.shipper_package_code = False


    def _compute_length_uom_name(self):
        # FIXME This variable does not impact any logic, it is only used for the packaging display on the form view.
        #  However, it generates some confusion for the users since this UoM will be ignored when sending the requests
        #  to the carrier server: the dimensions will be expressed with another UoM and there won't be any conversion.
        #  For instance, with Fedex, the UoM used with the package dimensions will depend on the UoM of
        #  `fedex_weight_unit`. With UPS, we will use the UoM defined on `ups_package_dimension_unit`
        self.length_uom_name = ""

    def _compute_weight_uom_name(self):
        for packaging in self:
            packaging.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()
