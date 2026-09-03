from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('fa3_pl', "Polish FA3")])

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        if self.country_code == 'PL':
            return 'fa3_pl'
        return super()._get_suggested_invoice_edi_format()

    @api.model
    def _get_address_format(self):
        address_format = super()._get_address_format()
        if self.env.context.get('without_country_name'):
            address_format = address_format.replace('\n%(country_name)s', '')
        return address_format
