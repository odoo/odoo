# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


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
        store=True,
        readonly=False,
        compute="_compute_l10n_tw_edi_tax_type",
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

    @api.depends("country_id", "amount")
    def _compute_l10n_tw_edi_tax_type(self):
        for tax in self:
            if tax.country_id.code == "TW":
                tax.l10n_tw_edi_tax_type = "2" if tax.amount == 0 else "1"
            else:
                tax.l10n_tw_edi_tax_type = False

    @api.onchange('l10n_tw_edi_tax_type')
    def _onchange_l10n_tw_edi_tax_type(self):
        for tax in self:
            if tax.l10n_tw_edi_tax_type not in ["3", "4"]:
                tax.l10n_tw_edi_special_tax_type = False

    @api.constrains('l10n_tw_edi_tax_type', 'l10n_tw_edi_special_tax_type')
    def _check_special_tax_type_constrains(self):
        for tax in self:
            if tax.l10n_tw_edi_tax_type == "3" and tax.l10n_tw_edi_special_tax_type in ['1', '2', '3', '4', '5', '6', '7']:
                raise UserError(self.env._("Invalid special tax type for Duty free tax type."))
            if tax.l10n_tw_edi_tax_type in ["2", "3"] and tax.amount != 0:
                raise UserError(self.env._("Zero tax rate and Duty free tax type must have a tax amount of 0."))
