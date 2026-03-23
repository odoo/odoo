from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('ubl_sg_b2g', "Singapore (AGD B2G)")])

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        statutory_board_tag = self.env.ref(
            'l10n_sg_b2g.res_partner_category_statutory_board',
            raise_if_not_found=False,
        )
        if self.country_code == 'SG' and statutory_board_tag in self.category_id:
            return 'ubl_sg_b2g'
        return super()._get_suggested_invoice_edi_format()

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'ubl_sg_b2g':
            return self.env['account.edi.xml.sg_b2g']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_sg_b2g'] = {'countries': ['SG'], 'on_peppol': False, 'sequence': 100, 'embed_attachments': True}
        return formats_info
