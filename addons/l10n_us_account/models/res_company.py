# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _compute_show_invoice_tax(self):
        super()._compute_show_invoice_tax()
        for record in self:
            if record.account_fiscal_country_id.code == 'US':
                record.show_invoice_tax = False
