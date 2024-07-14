# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from .account_tax import CATALOG07


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_pe_edi_allowance_charge_reason_code = fields.Selection(
        selection=[
            ('00', 'Other Discounts'),
            ('50', 'Other Charges'),
            ('51', 'Perceptions of Internal Sales'),
            ('52', 'Perception to the Acquisition of Fuel'),
            ('53', 'Perception done to the Agent of Perception with Special Rate'),
            ('54', 'Other Charges Related to the Service'),
            ('55', 'Other Charges no Related to the Service'),
        ],
        string="Allowance or Charge reason",
        default=False,
        help="Catalog 53 of possible reasons of discounts")
    l10n_pe_edi_affectation_reason = fields.Selection(
        selection=CATALOG07,
        string="EDI Affect. Reason",
        store=True, readonly=False, compute='_compute_l10n_pe_edi_affectation_reason',
        help="Type of Affectation to the IGV, Catalog No. 07")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('tax_ids', 'price_unit')
    def _compute_l10n_pe_edi_affectation_reason(self):
        '''Indicates how the IGV affects the invoice line product it represents the Catalog No. 07 of SUNAT.
        NOTE: Not all the cases are supported for the moment, in the future we might add this as field in a special
        tab for this rare configurations.
        '''
        for line in self:
            taxes_with_code = line.tax_ids.filtered(lambda tax: tax.l10n_pe_edi_tax_code)
            if not taxes_with_code or line.display_type in ('tax', 'payment_term'):
                line.l10n_pe_edi_affectation_reason = False
            else:
                line.l10n_pe_edi_affectation_reason = taxes_with_code[0].l10n_pe_edi_affectation_reason
