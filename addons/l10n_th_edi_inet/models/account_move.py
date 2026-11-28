# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

# Reason codes of ETDA Rec. 3-2560, appendix B.3.
CREDIT_NOTE_REASONS = [
    ('CDNG01', "Price of products sold is reduced (products violate the agreed terms)"),
    ('CDNG02', "Defective products"),
    ('CDNG03', "Products short of the agreed amount"),
    ('CDNG04', "Miscalculated product prices higher than is the case"),
    ('CDNG05', "Products returned (not as described)"),
    ('CDNG99', "Other reasons for products (specify)"),
    ('CDNS01', "Price of service is reduced (service violates the agreed terms)"),
    ('CDNS02', "Service fees missing"),
    ('CDNS03', "Miscalculated service price higher than is the case"),
    ('CDNS04', "Termination of service contract"),
    ('CDNS99', "Other reasons for services (specify)"),
]
DEBIT_NOTE_REASONS = [
    ('DBNG01', "Increase in the price of products (products in excess of the agreed quantity)"),
    ('DBNG02', "Miscalculated price of products lower than is the case"),
    ('DBNG99', "Other reasons for products (specify)"),
    ('DBNS01', "Increased service charges (services exceed the agreed terms)"),
    ('DBNS02', "Miscalculated price of services lower than is the case"),
    ('DBNS99', "Other reasons for services (specify)"),
]
OTHER_REASON_CODES = ('CDNG99', 'CDNS99', 'DBNG99', 'DBNS99')


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'l10n_th_edi_inet.document']

    l10n_th_edi_credit_note_reason = fields.Selection(
        selection=CREDIT_NOTE_REASONS,
        string="Credit Note Reason",
        copy=False,
    )
    l10n_th_edi_debit_note_reason = fields.Selection(
        selection=DEBIT_NOTE_REASONS,
        string="Debit Note Reason",
        copy=False,
    )
    l10n_th_edi_other_reason = fields.Char(string="Other Reason", copy=False)
    l10n_th_edi_available_reasons = fields.Json(compute='_compute_l10n_th_edi_available_reasons')

    @api.depends('l10n_th_edi_state', 'l10n_th_tax_invoice_ids.l10n_th_edi_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if {move.l10n_th_edi_state, *move.l10n_th_tax_invoice_ids.mapped('l10n_th_edi_state')} & {'processing', 'signed', 'unknown'}:
                move.show_reset_to_draft_button = False

    @api.depends('invoice_line_ids.product_id')
    def _compute_l10n_th_edi_available_reasons(self):
        for move in self:
            move.l10n_th_edi_available_reasons = move._l10n_th_edi_get_available_reasons()

    def _l10n_th_edi_get_type_code(self):
        """ Return the ETDA document type code of the moves that are e-Tax documents by themselves. """
        self.ensure_one()
        if self.country_code != 'TH' or not self.l10n_th_is_vat_registered:
            return None
        if self.move_type == 'out_refund':
            return '81'
        if self.move_type == 'out_invoice' and self.debit_origin_id:
            return '80'
        return None

    def _l10n_th_edi_get_available_reasons(self):
        """ Return the codes of the credit and debit note reasons that fit these customer documents, none if they are
        not e-Tax documents. When all their lines are goods, or all are services, only the codes for goods (xxxGnn)
        or for services (xxxSnn) fit. As in l10n_it_edi, a line without a product is goods. """
        if not all(move.is_sale_document() and move.country_code == 'TH' and move.l10n_th_is_vat_registered for move in self):
            return []
        line_kinds = {
            'S' if line.product_id.type == 'service' else 'G'
            for line in self.invoice_line_ids
            # The products of a combo are lines of their own.
            if line.display_type == 'product' and line.product_id.type != 'combo'
        }
        return [
            code for code, _label in CREDIT_NOTE_REASONS + DEBIT_NOTE_REASONS
            if len(line_kinds) != 1 or code[3] in line_kinds
        ]

    @api.model
    def _l10n_th_edi_get_reason_text(self, reason_code, other_reason):
        return other_reason if reason_code in OTHER_REASON_CODES else dict(CREDIT_NOTE_REASONS + DEBIT_NOTE_REASONS).get(reason_code)

    def _l10n_th_edi_get_document_values(self):
        self.ensure_one()
        type_code = self._l10n_th_edi_get_type_code()
        if type_code == '81':
            origin, reason_code = self.reversed_entry_id, self.l10n_th_edi_credit_note_reason
        else:
            origin, reason_code = self.debit_origin_id, self.l10n_th_edi_debit_note_reason
        amounts = self._l10n_th_get_credit_debit_note_amounts()
        return {
            'move': self,
            'type_code': type_code,
            'number': self.name,
            'date': self.invoice_date,
            'partner': self.commercial_partner_id,
            'currency': self.currency_id,
            'base_lines': self._get_th_tax_invoice_base_lines(self.invoice_line_ids.filtered(lambda line: line.display_type == 'product')),
            'tax_exigibility': None,
            'ratio': 1.0,
            'references': [
                {
                    'number': tax_invoice.tax_invoice_number,
                    'date': tax_invoice.date,
                    'type_code': 'T03' if tax_invoice.payment_move_id else '388',
                }
                for tax_invoice in origin.l10n_th_tax_invoice_ids.filtered(lambda tax_invoice: tax_invoice.state == 'posted')
            ],
            'purpose_code': reason_code,
            'purpose': self._l10n_th_edi_get_reason_text(reason_code, self.l10n_th_edi_other_reason),
            'original_amount': amounts and amounts[0]['amount'],
            'corrected_amount': amounts and amounts[1]['amount'],
        }

    def _l10n_th_edi_get_pdf_content(self):
        return self.env['ir.actions.report']._render_qweb_pdf('account.account_invoices', self.ids)[0]

    def _l10n_th_edi_check(self, document_values):
        # EXTENDS 'l10n_th_edi.document'
        errors = super()._l10n_th_edi_check(document_values)
        if not document_values['purpose']:
            errors.append(self.env._("Set the reason of %s.", self.name))
        if not document_values['references']:
            errors.append(self.env._("The original document of %s has no posted tax invoice to refer to.", self.name))
        return errors

    def _post(self, soft=True):
        # EXTENDS 'account'
        posted = super()._post(soft=soft)
        posted.filtered(
            lambda move: move._l10n_th_edi_get_type_code() and not move.l10n_th_edi_state,
        ).l10n_th_edi_state = 'ready_to_send'
        return posted

    def button_draft(self):
        # EXTENDS 'account'
        self.filtered(lambda move: move.l10n_th_edi_state in ('ready_to_send', 'error')).l10n_th_edi_state = False
        return super().button_draft()
