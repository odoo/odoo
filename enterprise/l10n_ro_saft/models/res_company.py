# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    l10n_ro_saft_tax_accounting_basis = fields.Selection(
        [
            ('A', 'A: general commercial companies using the general CoA for businesses'),
            ('I', 'I: non-residents and taxpayers with obligation to submit a special VAT return'),
            ('IFRS', 'IFRS: general commercial companies using the CoA for companies applying IFRS'),
            ('BANK', 'BANK: banks and financial instituttions using the CoA for financial institutions'),
            ('INSURANCE', 'INSURANCE: insurance companies using the CoA for insurance companies'),
            ('NORMA39', 'NORMA39: leasing and financial companies using the IFRS CoA according to ASF Reg. no. 39/2015'),
            ('IFN', 'IFN: non-bank financial institutions using the CoA of BNR Reg. no. 17/2015'),
            ('NORMA36', 'NORMA36: insurance and/or reinsurance brokerage companies using the CoA of ASF Reg. no. 36/2015'),
            ('NORMA14', 'NORMA14: private pension companies using the CoA of ASF Reg. no. 14/2015'),
        ],
        string='Tax Accounting Basis (RO)',
        help='The accounting regulations and Chart of Accounts used by this company',
    )
