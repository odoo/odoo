# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('fa3_pl', "Polish FA3")])

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        if self.country_code == 'PL':
            return 'fa3_pl'
        return super()._get_suggested_invoice_edi_format()
