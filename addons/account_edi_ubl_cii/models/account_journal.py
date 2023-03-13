# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import COUNTRY_EAS


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    checkbox_cii_xml = fields.Boolean(string='CII Billing', default=False)
    can_enable_cii_xml = fields.Boolean(compute='_compute_can_enable_ubl_cii_xml')

    checkbox_ubl_xml = fields.Boolean(string='BIS Billing', default=False)
    can_enable_ubl_xml = fields.Boolean(compute='_compute_can_enable_ubl_cii_xml')

    @api.depends('type', 'company_id')
    def _compute_can_enable_ubl_cii_xml(self):
        for journal in self:
            is_ubl_country = bool(journal._get_ubl_builder())
            is_cii_country = bool(journal._get_cii_builder())
            journal.can_enable_ubl_xml = journal.type == 'sale' and is_ubl_country
            journal.can_enable_cii_xml = journal.type == 'sale' and is_cii_country

    def _get_cii_builder(self):
        self.ensure_one()

        if self.country_code == 'FR':
            return self.env['account.edi.xml.cii'], {'facturx_pdfa': True}
        if self.country_code == 'DE':
            return self.env['account.edi.xml.cii'], {'facturx_pdfa': True}

    def _get_ubl_builder(self):
        self.ensure_one()

        if self.country_code == 'DE':
            return self.env['account.edi.xml.ubl_de'], {}
        if self.country_code in ('AU', 'NZ'):
            return self.env['account.edi.xml.ubl_a_nz'], {}
        if self.country_code == 'NL':
            return self.env['account.edi.xml.ubl_nl'], {}
        if self.country_code == 'SG':
            return self.env['account.edi.xml.ubl_sg'], {}
        if self.country_code in COUNTRY_EAS:
            return self.env['account.edi.xml.ubl_bis3'], {}
