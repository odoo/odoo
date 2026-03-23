from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_sg_statutory_board_subbusiness_unit = fields.Many2one(
        'l10n.sg.statutory.board.subbusiness.unit',
        string='Sub-Business Unit',
        domain="[('statutory_board_id', '=', commercial_partner_id)]",
    )
    l10n_sg_partner_is_statutory_board = fields.Boolean(
        compute='_compute_l10n_sg_partner_is_statutory_board',
    )
    l10n_sg_allowed_payment_term_ids = fields.Many2many(
        'account.payment.term',
        string='Allowed Payment Terms',
        compute='_compute_allowed_payment_terms',
    )
    l10n_sg_is_from_po_invoice = fields.Boolean(
        string='PO/II',
        help='Indicates if the invoice is generated from vendor provided purchase order or inventory instruction.',
        compute='_compute_l10n_sg_is_from_po_invoice',
        store=True,
        readonly=False,
    )

    @api.depends('commercial_partner_id.category_id')
    def _compute_l10n_sg_partner_is_statutory_board(self):
        statutory_board_tag = self.env.ref(
            'l10n_sg_b2g.res_partner_category_statutory_board',
            raise_if_not_found=False,
        )
        for move in self:
            move.l10n_sg_partner_is_statutory_board = (
                bool(statutory_board_tag and move.commercial_partner_id)
                and statutory_board_tag in move.commercial_partner_id.category_id
            )

    @api.depends('l10n_sg_partner_is_statutory_board', 'company_id')
    def _compute_allowed_payment_terms(self):
        rec = self.env['account.payment.term']._read_group(
            domain=[('company_id', 'in', [*self.company_id.ids, False])],
            groupby=['company_id', 'l10n_sg_b2g_code'],
            aggregates=['id:recordset'],
        )
        payment_term_dict = {}
        for company, l10n_sg_b2g_code, payment_terms in rec:
            payment_term_dict.setdefault(company, {}).setdefault(bool(l10n_sg_b2g_code), self.env['account.payment.term'])
            payment_term_dict[company][bool(l10n_sg_b2g_code)] |= payment_terms
        for move in self:
            company_payment_terms = payment_term_dict.get(move.company_id, {}) \
                .get(move.l10n_sg_partner_is_statutory_board, self.env['account.payment.term'])
            # All companies payment terms
            universal_payment_terms = payment_term_dict.get(self.env['res.company'], {}) \
                .get(move.l10n_sg_partner_is_statutory_board, self.env['account.payment.term'])
            move.l10n_sg_allowed_payment_term_ids = company_payment_terms | universal_payment_terms

    @api.depends('sale_order_count')
    def _compute_l10n_sg_is_from_po_invoice(self):
        for move in self:
            move.l10n_sg_is_from_po_invoice = move.l10n_sg_partner_is_statutory_board and move.sale_order_count > 0

    def _compute_invoice_payment_term_id(self):
        # EXTENDS account.move._compute_invoice_payment_term_id; unsets the payment term if it is not in the allowed list
        super()._compute_invoice_payment_term_id()
        for move in self:
            if move.company_id.account_fiscal_country_id.code != 'SG':
                continue
            if move.invoice_payment_term_id and move.invoice_payment_term_id.id not in move.l10n_sg_allowed_payment_term_ids.ids:
                move.invoice_payment_term_id = False


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_sg_b2g_invoice_line_no = fields.Char(
        string='SG B2G Invoice Line Number',
        compute='_compute_l10n_sg_b2g_invoice_line_no',
        store=True,
        readonly=False,
    )

    @api.depends('sale_line_ids.l10n_sg_ubl_line_item_ref', 'sequence')
    def _compute_l10n_sg_b2g_invoice_line_no(self):
        for line in self:
            line.l10n_sg_b2g_invoice_line_no = line.sale_line_ids.l10n_sg_ubl_line_item_ref
