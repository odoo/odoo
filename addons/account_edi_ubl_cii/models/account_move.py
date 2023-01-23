# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, tools, Command
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import COUNTRY_EAS


class AccountMove(models.Model):
    _inherit = 'account.move'

    ubl_cii_xml_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="UBL/CII Document",
        copy=False,
    )

    def _get_ubl_cii_builder(self):
        self.ensure_one()

        if self.country_code == 'DE':
            return self.env['account.edi.xml.ubl_de'], {'ubl_inject_pdf': True}
        if self.country_code == 'BE':
            return self.env['account.edi.xml.ubl_efff'], {'ubl_inject_pdf': True}
        if self.country_code in ('AU', 'NZ'):
            return self.env['account.edi.xml.ubl_a_nz'], {'ubl_inject_pdf': True}
        if self.country_code == 'FR':
            return self.env['account.edi.xml.cii'], {'embed_to_pdf': True, 'facturx_pdfa': True}
        if self.country_code == 'NL':
            return self.env['account.edi.xml.ubl_nl'], {'ubl_inject_pdf': True}
        if self.country_code in COUNTRY_EAS:
            return self.env['account.edi.xml.ubl_bis3'], {'ubl_inject_pdf': True}
