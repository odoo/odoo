# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api

INVOICE_TYPES_BY_USE = {
    'sale': ['F1', 'F2', 'F4'],
    'purchase': ['F1', 'F2', 'F4', 'F5', 'F6', 'LC'],
    'credit_note': ['R1', 'R2', 'R3', 'R4', 'R5'],
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_original_invoice_credited = fields.Char(string='Original Invoice Credited', store=False)
    l10n_es_invoice_type_available = fields.Char(
        string='Invoice Types Available',
        compute='_compute_l10n_es_invoice_type_available'
    )
    l10n_es_invoice_type = fields.Selection(
        selection='l10n_es_invoice_type_selection',
        compute='_compute_l10n_es_invoice_type',
        store=True, readonly=False,
        copy=False,
        help="For credit notes (R1-R5), also identifies the Article 80 (Law 37/1992, BOE-A-1992-28740) "
            "reason for modifying the taxable base."
    )
    l10n_es_available_regime_codes = fields.Char(
        string="Available VAT Regime Codes",
        compute="_compute_l10n_es_available_regime_codes",
        help="Technical field to enable a dynamic selection of the field \"VAT Regime Code\"",
    )
    l10n_es_regime_code = fields.Selection(
        string="VAT Regime Code",
        selection="_l10n_es_regime_code_selection",
        compute="_compute_l10n_es_regime_code",
        store=True, readonly=False,
    )
    l10n_es_regime_code_additional = fields.Selection(
        string="VAT Regime Code (Additional)",
        selection="_l10n_es_regime_code_selection",
        compute="_compute_l10n_es_regime_code",
        store=True, readonly=False,
    )

    @api.depends('move_type')
    def _compute_l10n_es_invoice_type_available(self):
        for move in self:
            if move.move_type == 'out_invoice':
                move.l10n_es_invoice_type_available = ','.join(INVOICE_TYPES_BY_USE['sale'])
            elif move.move_type == 'in_invoice':
                move.l10n_es_invoice_type_available = ','.join(INVOICE_TYPES_BY_USE['purchase'])
            elif move.move_type in ('out_refund', 'in_refund'):
                move.l10n_es_invoice_type_available = ','.join(INVOICE_TYPES_BY_USE['credit_note'])
            else:
                move.l10n_es_invoice_type_available = ''

    # Sale:
    #   * no VAT and under the limit -> the move must be simplified (F2/R5);
    #   * VAT and over the limit     -> the move cannot be simplified, normalise back to F1/R4;
    #   * otherwise, keep what's set or default on VAT presence.
    # Purchase: F1/R4, or F5/F6 derived from the bill's taxes.
    # Depends on 'invoice_line_ids.price_total' (not 'amount_total_signed') so the limit
    # re-evaluates right after adding a line.
    @api.depends('move_type', 'partner_id', 'invoice_line_ids.price_total',
                 'invoice_line_ids.tax_ids.l10n_es_type', 'amount_total_signed')
    def _compute_l10n_es_invoice_type(self):
        simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
        europe = self.env.ref('base.europe')
        for move in self:
            if move.state == 'posted' and move.l10n_es_invoice_type:
                continue

            if move.country_code != 'ES':
                move.l10n_es_invoice_type = False
                continue

            currency = move.currency_id or move.company_id.currency_id

            # Signal that forces an invoice/refund to a simplified type regardless of amount/VAT
            # (receipts are always simplified -- see the branch below -- so this never applies to them).
            explicit_simplified = bool(simplified_partner and move.partner_id == simplified_partner)

            # VAT + amount-limit criterion, sale side only (see the comment on the method above).
            explicit_regular = False
            if (move.move_type in ('out_invoice', 'out_refund') and move.commercial_partner_id.country_id in europe.country_ids):
                has_vat = move.commercial_partner_id.has_vat
                total_amount = sum(move.invoice_line_ids.filtered(
                    lambda line: line.display_type == 'product').mapped('price_total'))
                under_limit = currency.compare_amounts(
                    total_amount, move.company_id.l10n_es_simplified_invoice_limit) <= 0
                explicit_simplified = explicit_simplified or (not has_vat and under_limit)
                explicit_regular = has_vat and not under_limit

            if move.move_type in ('out_invoice', 'in_invoice'):
                if explicit_simplified:
                    move.l10n_es_invoice_type = 'F2'
                elif explicit_regular and move.l10n_es_invoice_type in (False, 'F2'):
                    move.l10n_es_invoice_type = 'F1'
                elif move.move_type == 'out_invoice' and not move.l10n_es_invoice_type:
                    move.l10n_es_invoice_type = 'F1' if move.commercial_partner_id.has_vat else 'F2'
                elif move.move_type == 'in_invoice' and not move.l10n_es_invoice_type:
                    move.l10n_es_invoice_type = 'F1'
                # Vendor bills under the REAGYP or DUA regimes must be classified F6/F5
                # respectively. Same guard as above: only auto-adjust while still at the generic
                # default, never override an explicit user choice.
                if move.move_type == 'in_invoice' and move.l10n_es_invoice_type in (False, 'F1'):
                    reagyp = move.invoice_line_ids.tax_ids.filtered(lambda t: t.l10n_es_type == 'sujeto_agricultura')
                    if reagyp:
                        move.l10n_es_invoice_type = 'F6'
                    elif move._l10n_es_is_dua():
                        move.l10n_es_invoice_type = 'F5'
            elif move.move_type in ('out_refund', 'in_refund'):
                if explicit_simplified:
                    move.l10n_es_invoice_type = 'R5'
                elif explicit_regular and move.l10n_es_invoice_type in (False, 'R5'):
                    move.l10n_es_invoice_type = 'R4'
                elif move.move_type == 'out_refund' and not move.l10n_es_invoice_type:
                    move.l10n_es_invoice_type = 'R4' if move.commercial_partner_id.has_vat else 'R5'
                elif move.move_type == 'in_refund' and not move.l10n_es_invoice_type:
                    move.l10n_es_invoice_type = 'R4'
            elif move.move_type in ('out_receipt', 'in_receipt'):
                # Receipts are always simplified: anything else would require identifying the
                # customer, at which point it stops being a receipt and becomes a proper invoice.
                move.l10n_es_invoice_type = 'F2'
            else:
                move.l10n_es_invoice_type = False

    @api.depends('move_type', 'invoice_line_ids.tax_ids', 'invoice_line_ids.tax_ids.l10n_es_applicability')
    def _compute_l10n_es_available_regime_codes(self):
        for move in self:
            use = 'purchase' if move.is_purchase_document(include_receipts=True) else 'sale'
            valid = move.company_id._l10n_es_regime_available_codes(
                use, applicability=move._l10n_es_get_tax_applicability())
            move.l10n_es_available_regime_codes = ','.join(valid) if valid else False

    @api.depends('move_type', 'invoice_line_ids.tax_ids', 'invoice_line_ids.tax_ids.l10n_es_regime_code',
                 'invoice_line_ids.tax_ids.children_tax_ids.l10n_es_regime_code',
                 'company_id.l10n_es_special_vat_regime')
    def _compute_l10n_es_regime_code(self):
        regime_code_priorities = {
            '07': 0,
            '05': 1,
            '03': 2,
            '08': 2,
        }
        for move in self:
            if move.state == 'posted' and move.l10n_es_regime_code:
                continue
            default_code = move.company_id._l10n_es_special_vat_regime_codes().get(move.company_id.l10n_es_special_vat_regime, '01')
            lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')

            regime_codes = set()
            for line in lines:
                # Flattened: a group tax carries no regime code of its own, only its children do.
                line_codes = [code for code in line.tax_ids.flatten_taxes_hierarchy().mapped('l10n_es_regime_code') if code]
                if line_codes:
                    regime_codes.update(line_codes)
                else:
                    regime_codes.add(default_code)

            sorted_regime_codes = sorted(regime_codes, key=lambda code: (regime_code_priorities.get(code, 99), code))
            move.l10n_es_regime_code = sorted_regime_codes[0] if sorted_regime_codes else default_code
            move.l10n_es_regime_code_additional = sorted_regime_codes[1] if len(sorted_regime_codes) > 1 else False

    @api.model
    def _l10n_es_refund_reason_selection(self):
        _ = self.env._
        return [
            ('R1', _("R1: Art. 80.1, 80.2, 80.6 and rights founded error")),
            ('R2', _("R2: Art. 80.3")),
            ('R3', _("R3: Art. 80.4")),
            ('R4', _("R4: Art. 80 - other")),
            ('R5', _("R5: Corrective invoice for simplified invoices")),
        ]

    @api.model
    def l10n_es_invoice_type_selection(self):
        _ = self.env._
        labels = [
            ('F1', _("F1 Invoice")),
            ('F2', _("F2 Simplified Invoice")),
            ('F4', _("F4 Summary of Invoices")),
            ('F5', _("F5 Importations (DUA)")),
            ('F6', _("F6 Accounting Vouchers")),
            ('LC', _("LC Customs")),
        ]
        return sorted(labels + self._l10n_es_refund_reason_selection())

    def _l10n_es_is_dua(self):
        self.ensure_one()
        return any(t.l10n_es_type == 'dua' for t in self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy())

    @api.model
    def _l10n_es_regime_code_selection(self):
        # Reuse account.tax's catalog (already extended by each installed EDI module) instead of
        # duplicating it here.
        return self.env['account.tax']._l10n_es_regime_code_selection()

    def _l10n_es_get_tax_applicability(self):
        """Return the l10n_es_applicability of this move's taxes (see `account.tax._l10n_es_get_applicability`)."""
        self.ensure_one()
        taxes = self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy()
        return taxes._l10n_es_get_applicability()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        default_values_list = default_values_list or [{}] * len(self)
        for move, default_values in zip(self, default_values_list):
            is_simplified = move.l10n_es_invoice_type in ('F2', 'R5')
            default_values.setdefault('l10n_es_invoice_type', 'R5' if is_simplified else 'R4')
        return super()._reverse_moves(
            default_values_list=default_values_list,
            cancel=cancel,
        )
