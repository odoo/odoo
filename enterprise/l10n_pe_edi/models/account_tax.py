# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


CATALOG07 = [
    ('10', 'Taxed- Onerous Operation'),
    ('11', 'Taxed- Withdrawal by Prize'),
    ('12', 'Taxed- Withdrawal by Donation'),
    ('13', 'Taxed- Withdrawal'),
    ('14', 'Taxed- Withdrawal by Advertising'),
    ('15', 'Taxed- Bonus'),
    ('16', 'Taxed- Withdrawal by delivery to workers'),
    ('17', 'Taxed- IVAP'),
    ('20', 'Exonerated- Onerous Operation'),
    ('21', 'Exonerated- Free Transfer'),
    ('30', 'Unaffected- Onerous Operation'),
    ('31', 'Unaffected- Withdrawal by Bonus'),
    ('32', 'Unaffected- Withdrawal'),
    ('33', 'Unaffected- Withdrawal by Medical Samples'),
    ('34', 'Unaffected- Withdrawal by Collective Agreement'),
    ('35', 'Unaffected- Withdrawal by Prize'),
    ('36', 'Unaffected- Withdrawal by Advertising'),
    ('37', 'Unaffected- Free Transfer'),
    ('40', 'Exportation')
]


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_pe_edi_affectation_reason = fields.Selection(
        selection=CATALOG07,
        string="Affectation Reason",
        store=True, readonly=False, compute='_compute_l10n_pe_edi_affectation_reason',
        help="Peru: Type of Affectation to the IGV, Catalog No. 07.")
    l10n_pe_edi_international_code = fields.Char(
        string="EDI International Code",
        compute='_compute_l10n_pe_edi_international_code')

    @api.depends('l10n_pe_edi_tax_code')
    def _compute_l10n_pe_edi_affectation_reason(self):
        ''' Indicates how the IGV affects the invoice line product it represents the Catalog No. 07 of SUNAT.
        NOTE: Not all the cases are supported for the moment, in the future we might add this as field in a special
        tab for this rare configurations.
        '''
        tax_comparison = {
            '1000': '10',
            '9996': '11',
            '1016': '17',
            '9997': '20',
            '9998': '30',
            '9995': '40'
        }
        for tax in self:
            tax.l10n_pe_edi_affectation_reason = tax_comparison.get(tax.l10n_pe_edi_tax_code, False)

    @api.depends('l10n_pe_edi_tax_code')
    def _compute_l10n_pe_edi_international_code(self):
        international_codes_mapping = {
            '1000': 'VAT',
            '1016': 'VAT',
            '2000': 'EXC',
            '7152': 'OTH',
            '9995': 'FRE',
            '9996': 'FRE',
            '9997': 'VAT',
            '9998': 'FRE',
            '9999': 'OTH',
        }
        for tax in self:
            tax.l10n_pe_edi_international_code = international_codes_mapping.get(tax.l10n_pe_edi_tax_code, 'VAT')
