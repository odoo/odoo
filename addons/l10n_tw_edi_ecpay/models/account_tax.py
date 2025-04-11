# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_tw_edi_tax_type = fields.Selection(
        string="Ecpay Tax Type",
        selection=[
            ("1", "Taxable"),
            ("2", "Zero tax rate"),
            ("3", "Duty free"),
            ("4", "Taxable (special tax rate)"),
        ],
        default="1",
    )
    l10n_tw_edi_special_tax_type = fields.Selection(
        string="Ecpay Special Tax Type",
        selection=[
            ("1", "Saloons and tea rooms, coffee shops and bars offering companionship services: Tax rate is 25%"),
            ("2", "Night clubs or restaurants providing entertaining show programs: Tax rate is 15%"),
            ("3", "Banking businesses, insurance businesses, trust investment businesses, securities businesses, "
                "futures businesses, commercial paper businesses and pawn-broking businesses: Tax rate is 2%"),
            ("4", "The sales amounts from reinsurance premiums shall be taxed at 1%"),
            ("5", "Banking businesses, insurance businesses, trust investment businesses, securities businesses, "
                "futures businesses, commercial paper businesses and pawn-broking businesses: Tax rate is 5%"),
            ("6", "Core business revenues from the banking and insurance business of the banking and insurance "
                "industries (Applicable to sales after July 2014): Tax rate is 5%"),
            ("7", "Core business revenues from the banking and insurance business of the banking and insurance "
                "industries (Applicable to sales after June 2014): Tax rate is 5%"),
            ("8", "Duty free or non-output data"),
        ],
    )
