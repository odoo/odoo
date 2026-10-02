# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from .res_partner import L10N_KR_ISSUANCE_TYPES

# Proofs of issuance that contradict a given tax group, keyed by tax group template xmlid.
L10N_KR_SALE_ISSUANCE_CONFLICTS = {
    'tax_group_vat': {'tax_exempt_invoice'},
    'tax_group_zero_rate': {'tax_exempt_invoice', 'purchaser_tax_invoice'},
    'tax_group_exempt': {'tax_invoice', 'purchaser_tax_invoice'},
}
L10N_KR_PURCHASE_ISSUANCE_CONFLICTS = {
    'tax_group_vat': {'tax_exempt_invoice', 'other'},
    'tax_group_zero_rate': {'tax_exempt_invoice', 'purchaser_tax_invoice', 'card_payment', 'cash_receipt', 'other'},
    'tax_group_exempt': {'tax_invoice', 'purchaser_tax_invoice'},
    'tax_group_vat_dp': {'tax_invoice', 'purchaser_tax_invoice'},
    'tax_group_vat_rp': {'tax_invoice', 'tax_exempt_invoice', 'purchaser_tax_invoice'},
    'tax_group_sub_base': {'tax_exempt_invoice', 'purchaser_tax_invoice', 'card_payment', 'cash_receipt', 'other'},
}
# A (tax-exempt) invoice covers a single tax type: VAT 10%, VAT 0% or tax-exempt supplies, never a mix.
L10N_KR_SINGLE_NATURE_ISSUANCE_TYPES = {'tax_invoice', 'tax_exempt_invoice', 'purchaser_tax_invoice'}
L10N_KR_SINGLE_NATURE_TAX_GROUPS = {'tax_group_vat', 'tax_group_zero_rate', 'tax_group_exempt'}


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
        copy=False,
        help="Official HomeTax or PG approval number (24 digits for e-Tax Invoices, 9 digits for Cash Receipts).",
    )

    @api.depends('commercial_partner_id', 'country_code')
    def _compute_l10n_kr_issuance_type(self):
        for move in self:
            if move.country_code == 'KR':
                move.l10n_kr_issuance_type = move.commercial_partner_id.l10n_kr_default_issuance_type
            else:
                move.l10n_kr_issuance_type = False

    def write(self, vals):
        if 'l10n_kr_issuance_type' in vals:
            # The proof of issuance dispatches the move into the VAT report boxes.
            self.filtered(
                lambda m: m.l10n_kr_issuance_type != vals['l10n_kr_issuance_type']
            ).line_ids._check_tax_lock_date()
        return super().write(vals)

    @api.depends('l10n_kr_issuance_type', 'invoice_line_ids.tax_ids')
    def _compute_alerts(self):
        # EXTENDS 'account'
        super()._compute_alerts()

    def _get_alerts(self):
        # EXTENDS 'account'
        alerts = super()._get_alerts()
        issuance_type = self.l10n_kr_issuance_type
        if self.country_code != 'KR' or self.state == 'cancel' or not self.is_invoice(include_receipts=True):
            return alerts

        ChartTemplate = self.env['account.chart.template'].with_company(self.company_id)
        conflicts = L10N_KR_SALE_ISSUANCE_CONFLICTS if self.is_sale_document(include_receipts=True) else L10N_KR_PURCHASE_ISSUANCE_CONFLICTS
        # Group taxes (e.g. 10% IM) carry no meaningful tax group of their own: look at their children instead.
        tax_groups = self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy().tax_group_id
        used_group_xmlids = {
            xmlid
            for xmlid in conflicts
            if (tax_group := ChartTemplate.ref(xmlid, raise_if_not_found=False)) and tax_group in tax_groups
        }

        if (
            (not issuance_type or issuance_type in L10N_KR_SINGLE_NATURE_ISSUANCE_TYPES)
            and len(used_group_xmlids & L10N_KR_SINGLE_NATURE_TAX_GROUPS) >= 2
        ):
            alerts['l10n_kr_mixed_tax_nature'] = {
                'level': 'warning',
                'message': self.env._("This invoice mixes items with different tax types (VAT 10%, VAT 0%, tax-exempt), consider splitting into separate invoices."),
            }
        elif any(issuance_type in conflicts[xmlid] for xmlid in used_group_xmlids):
            alerts['l10n_kr_issuance_type_mismatch'] = {
                'level': 'warning',
                'message': self.env._(
                    "The proof of issuance doesn't seem to match the tax on this invoice. "
                    "Please check the tax or the proof of issuance so it's reported correctly in your VAT return.",
                ),
            }
        return alerts
