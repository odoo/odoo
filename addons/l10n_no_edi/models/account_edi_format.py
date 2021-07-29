# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _get_edi_ubl_info_hook(self, company_country_code):
        # OVERRIDE

        # EHF (NO)
        if self.code == 'ubl_bis3' and company_country_code == 'NO':
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_no'],
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl.xml",
            }

        return super()._get_edi_ubl_info_hook(company_country_code)
