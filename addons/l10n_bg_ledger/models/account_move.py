from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_bg_document_type = fields.Selection(
        string="Document Type (BG)",
        selection='_l10n_bg_document_type_selection_values',
        compute='_compute_l10n_bg_document_type',
        readonly=False,
        store=True,
        copy=False,
    )
    l10n_bg_document_number = fields.Char(string="Document Number (BG)", compute='_compute_l10n_bg_document_number')
    l10n_bg_exemption_reason = fields.Selection(string="Exemption reason (BG)", selection=[
        ('01', '01 - A delivery under Part 1 of Appendix 2 of LVAT'),
        ('02', '02 - A delivery under Part 2 of Appendix 2 of LVAT'),
        ('03', '03 - Import under Appendix 3 of VAT act'),
    ])

    def _l10n_bg_document_type_selection_values(self):
        return [
            ('01', '01 - Invoice'),
            ('02', '02 - Debit notice'),
            ('03', '03 - Credit notice'),
            ('07', '07 - Customs declaration'),
            ('09', '09 - Protocol or another document'),
            ('11', '11 - Invoice - cash account'),
            ('12', '12 - Debit notification - cash account'),
            ('13', '13 - Credit notification - cash account'),
            ('81', '81 - Report for the sales carried out'),
            ('82', '82 - Report for the sales carried out by a special levying procedure'),
            ('91', '91 - Protocol of due tax under Art. 151c, Para 3 of the Act'),
            ('93', '93 - Protocol of due tax under Art. 151c, Para 7 of the Act with a recipient being a person not applying the special regime'),
            ('94', '94 - Protocol of due tax under Art. 151c, Para 7 of the Act with a recipient being a person applying the special regime'),
        ]

    @api.depends('journal_id', 'move_type')
    def _compute_l10n_bg_document_type(self):
        for move in self:
            if move.journal_id:
                if 'debit_origin_id' in self._fields and move.debit_origin_id:
                    move.l10n_bg_document_type = move.journal_id.l10n_bg_debit_notes
                elif move.move_type in ('out_invoice', 'in_invoice'):
                    move.l10n_bg_document_type = move.journal_id.l10n_bg_customer_invoice
                elif move.move_type in ('in_refund', 'out_refund'):
                    move.l10n_bg_document_type = move.journal_id.l10n_bg_credit_notes

    @api.depends('l10n_bg_document_type', 'move_type', 'state', 'ref', 'name')
    def _compute_l10n_bg_document_number(self):
        for move in self:
            if move.state == 'draft':
                move.l10n_bg_document_number = ""
            elif move.is_sale_document(include_receipts=True):
                move.l10n_bg_document_number = move.name
            else:
                move.l10n_bg_document_number = move.ref
