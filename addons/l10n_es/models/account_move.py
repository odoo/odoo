# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = ['account.move', 'l10n.es.vat.regime.mixin']
    _name = 'account.move'

    _INVOICE_TYPES_BY_USE = {
        'sale': ['F1', 'F2', 'F4'],
        'purchase': ['F1', 'F2', 'F4', 'F5', 'F6', 'LC'],
        'credit_note': ['R1', 'R2', 'R3', 'R4', 'R5'],
    }

    l10n_es_is_simplified = fields.Boolean("Is Simplified",
                                           compute="_compute_l10n_es_is_simplified", readonly=False, store=True)

    l10n_es_original_invoice_credited = fields.Char(string='Original Invoice Credited', store=False)

    l10n_es_invoice_type_available = fields.Char(string='Invoice Types Available',
                                                 compute='_compute_l10n_es_invoice_type_available')

    l10n_es_invoice_type = fields.Selection(selection='l10n_es_invoice_type_selection',
                                            copy=False)

    # Note: We depend on 'line_ids.balance' instead of 'amount_total_signed' directly.
    # Otherwise the field is recomputed when the 'state' changes (since 'amount_total_signed' depends on it);
    # the recomputation would i.e. happen when confirming the invoice and override any manual edits of the field.
    @api.depends('partner_id', 'line_ids.balance')
    def _compute_l10n_es_is_simplified(self):
        simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
        for move in self:
            currency_id = move.currency_id or move.company_id.currency_id
            move.l10n_es_is_simplified = (move.country_code == 'ES') and (
                (not move.partner_id and move.move_type in ('in_receipt', 'out_receipt'))
                or (simplified_partner and move.partner_id == simplified_partner)
                or (move.move_type in ('out_invoice', 'out_refund')
                    and not move.commercial_partner_id.vat
                    and currency_id.compare_amounts(abs(move.amount_total_signed), move.company_id.l10n_es_simplified_invoice_limit) <= 0
                    and move.commercial_partner_id.country_id in self.env.ref('base.europe').country_ids
                )
            )

    def _l10n_es_is_dua(self):
        self.ensure_one()
        return any(t.l10n_es_type == 'dua' for t in self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy())

    @api.model
    def l10n_es_invoice_type_selection(self):
        return sorted([
            ('F1', 'F1 Factura'),
            ('F2', 'F2 Factura Simplificada'),
            ('F4', 'F4 Asiento Resumen de Facturas'),
            ('F5', 'F5 Importaciones (DUA)'),
            ('F6', 'F6 Justificantes Contables'),
            ('LC', 'LC Aduanas'),
            ('R1', 'R1'),
            ('R2', 'R2'),
            ('R3', 'R3'),
            ('R4', 'R4'),
            ('R5', 'R5'),
        ])

    @api.depends('move_type')
    def _compute_l10n_es_invoice_type_available(self):
        for move in self:
            if move.move_type == 'out_invoice':
                move.l10n_es_invoice_type_available = ','.join(code for code in self._INVOICE_TYPES_BY_USE['sale'])
            elif move.move_type == 'in_invoice':
                move.l10n_es_invoice_type_available = ','.join(code for code in self._INVOICE_TYPES_BY_USE['purchase'])
            elif move.move_type in ('out_refund', 'in_refund'):
                move.l10n_es_invoice_type_available = ','.join(
                    code for code in self._INVOICE_TYPES_BY_USE['credit_note'])
            else:
                move.l10n_es_invoice_type_available = ''

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        move_type = defaults.get('move_type') or self.env.context.get('default_move_type')
        if move_type in ('out_invoice', 'in_invoice'):
            defaults['l10n_es_invoice_type'] = 'F1'
        elif move_type in ('out_refund', 'in_refund'):
            defaults['l10n_es_invoice_type'] = 'R4'
        return defaults

    @api.onchange('move_type', 'l10n_es_is_simplified')
    def _onchange_l10n_es_invoice_type(self):
        if self.move_type in ('out_invoice', 'in_invoice'):
            self.l10n_es_invoice_type = 'F2' if self.l10n_es_is_simplified else 'F1'
        elif self.move_type in ('out_refund', 'in_refund'):
            self.l10n_es_invoice_type = 'R5' if self.l10n_es_is_simplified else 'R4'

    def _l10n_es_vat_regime_get_use(self):
        self.ensure_one()
        return 'sale' if self.move_type in ('out_invoice', 'out_refund') else 'purchase'

    @api.depends('move_type')
    def _compute_l10n_es_vat_regime_available(self):
        super()._compute_l10n_es_vat_regime_available()

    @api.depends('move_type', 'invoice_line_ids.tax_ids')
    def _compute_l10n_es_vat_regime_codes(self):
        super()._compute_l10n_es_vat_regime_codes()
        for move in self:
            tax = next(
                (t for line in move.invoice_line_ids
                 if line.display_type == 'product'
                 for t in line.tax_ids),
                self.env['account.tax']
            )
            move.l10n_es_vat_regime_code_id = tax.l10n_es_vat_regime_code_id or False
            move.l10n_es_vat_regime_code_additional = tax.l10n_es_vat_regime_code_additional or False

    def _reverse_moves(self, default_values_list=None, cancel=False):
        default_values_list = default_values_list or [{}] * len(self)
        for move, default_values in zip(self, default_values_list):
            is_simplified = move.l10n_es_is_simplified
            default_values.setdefault('l10n_es_invoice_type', 'R5' if is_simplified else 'R4')
        return super()._reverse_moves(
            default_values_list=default_values_list,
            cancel=cancel,
        )
