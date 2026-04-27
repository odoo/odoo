# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PackageType(models.Model):
    _inherit = 'stock.package.type'

    package_carrier_type = fields.Selection(selection_add=[('shiprocket', 'Shiprocket')])

    @api.constrains('packaging_length', 'width', 'height', 'package_carrier_type')
    def _check_shiprocket_required_value(self):
        for record in self:
            if record.package_carrier_type == 'shiprocket' and \
                    any(dim <= 0 for dim in (record.packaging_length, record.width, record.height)):
                raise ValidationError(_('Length, Width and Height is necessary for Shiprocket Package.'))

    @api.depends('package_carrier_type')
    def _compute_length_uom_name(self):
        super()._compute_length_uom_name()
        for package in self.filtered(lambda p: p.package_carrier_type == 'shiprocket'):
            package.length_uom_name = 'cm'
