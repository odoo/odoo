from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('fa3_pl', "Polish FA3")])

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        if self.country_code == 'PL':
            return 'fa3_pl'
        return super()._get_suggested_invoice_edi_format()
