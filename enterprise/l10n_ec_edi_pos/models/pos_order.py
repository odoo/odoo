from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_invoice_vals(self):
        # EXTENDS 'point_of_sale'
        vals = super()._prepare_invoice_vals()
        if self.company_id.country_id.code == 'EC':
            if len(self.payment_ids) > 1:
                vals['l10n_ec_sri_payment_id'] = self.env['l10n_ec.sri.payment'].search([("code", "=", "mpm")]).id
            else:
                vals['l10n_ec_sri_payment_id'] = self.payment_ids.payment_method_id.l10n_ec_sri_payment_id.id
        return vals
