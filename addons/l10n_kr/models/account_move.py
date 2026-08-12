# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from .res_partner import L10N_KR_ISSUANCE_TYPES


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_kr_issuance_type = fields.Selection(
        # A purchaser-issued tax invoice only ever exists on a move, never as a partner default or
        # on a sale order, so it is added on top of the shared list rather than part of it.
        selection=[*L10N_KR_ISSUANCE_TYPES, ('purchaser_tax_invoice', "Tax Invoice issued by Purchaser")],
        string="Proof of Issuance",
        tracking=True,
        compute='_compute_l10n_kr_issuance_type',
        store=True,
        readonly=False,
        help="South Korean government-verified proof of issuance used to legally justify this transaction. "
             "Drives which VAT report boxes the transaction is reported under.",
    )
    l10n_kr_edocument_number = fields.Char(
        string="e-Document Number",
        help="Official HomeTax or PG approval number (24 digits for e-Tax Invoices, 9 digits for Cash Receipts).",
    )

    @api.depends('commercial_partner_id', 'country_code')
    def _compute_l10n_kr_issuance_type(self):
        for move in self:
            if move.country_code == 'KR':
                move.l10n_kr_issuance_type = move.commercial_partner_id.l10n_kr_default_issuance_type
            else:
                move.l10n_kr_issuance_type = False
