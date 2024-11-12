# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class DecimalPrecision(models.Model):
    _inherit = 'decimal.precision'

    @api.onchange('digits')
    def _onchange_digits(self):
        if self.name != "Product Unit of Measure":  # precision_get() relies on this name
            return
        # We are changing the precision of UOM fields; check whether the
        # precision is equal or higher than existing units of measure.
        rounding = 1.0 / 10.0**self.digits
        dangerous_uom = self.env['uom.uom'].search([('rounding', '<', rounding)])
        if dangerous_uom:
            uom_descriptions = [
                " - %s (id=%s, precision=%s)" % (uom.name, uom.id, uom.rounding)
                for uom in dangerous_uom
            ]
            return {'warning': {
                'title': _('Warning!'),
                'message': _(
                    "You are setting a Decimal Accuracy less precise than the UOMs:\n"
                    "%s\n"
                    "This may cause inconsistencies in computations.\n"
                    "Please increase the rounding of those units of measure, or the digits of this Decimal Accuracy.",
                    '\n'.join(uom_descriptions)),
            }}
