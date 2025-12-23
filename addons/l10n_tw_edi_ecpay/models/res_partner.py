# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('tw_ecpay', "ECPay")])

    def _l10n_tw_edi_formatted_address(self):
        address = self._display_address(without_company=True)
        return ", ".join(filter(None, map(str.strip, address.splitlines())))
