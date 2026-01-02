from odoo import models, fields, api
from odoo.exceptions import ValidationError

TIMEOUT = 10


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_sending_method = fields.Selection(
        selection_add=[('mojeracun', 'by MojEracun')],
    )
    invoice_edi_format = fields.Selection(selection_add=[('ubl_hr', "CIUS HR")])
    l10n_hr_personal_oib = fields.Char(string="Personal OIB")
    l10n_hr_business_unit_code = fields.Char("Business Unit Code", default=None)

    # -------------------------------------------------------------------------
    # CONSTRAINT
    # -------------------------------------------------------------------------

    @api.constrains('invoice_edi_format', 'invoice_sending_method')
    def _check_mojeracun_send_ubl_hr(self):
        if self.filtered(lambda partner: partner.invoice_edi_format != 'ubl_hr' and partner.invoice_sending_method == 'mojeracun'):
            raise ValidationError(self.env._('On MojEracun, only the Croatian UBL format is supported.'))

    # -------------------------------------------------------------------------
    # OVERRIDE AND HELPERS
    # -------------------------------------------------------------------------

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'ubl_hr':
            return self.env['account.edi.xml.ubl_hr']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_hr'] = {'countries': ['HR'], 'on_peppol': False}
        return formats_info

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        if self.country_code == 'HR':
            return 'ubl_hr'
        return super()._get_suggested_invoice_edi_format()
