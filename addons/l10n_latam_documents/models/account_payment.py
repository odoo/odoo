# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class AccountPayment(models.Model):

    _inherit = "account.payment"

    l10n_latam_document_number = fields.Char(
        string='Document Number',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        index=True,
    )
    l10n_latam_document_sequence_id = fields.Many2one(
        related='l10n_latam_receiptbook_id.sequence_id',
        readonly=True,
    )
    l10n_latam_use_documents = fields.Boolean(
        related='company_id.l10n_latam_use_documents',
    )
    l10n_latam_receiptbook_id = fields.Many2one(
        'l10n_latam.payment.receiptbook',
        'ReceiptBook',
        readonly=True,
        states={'draft': [('readonly', False)]},
        auto_join=True,
    )
    l10n_latam_document_type_id = fields.Many2one(
        related='l10n_latam_receiptbook_id.document_type_id',
        readonly=True,
    )
    l10n_latam_next_number = fields.Integer(
        compute='_compute_next_number',
        string='Next Number',
    )
    display_name = fields.Char(
        compute='_compute_display_name',
        search='_search_display_name',
        string='Document Reference',
    )

    @api.model
    def _search_display_name(self, operator, operand):
        domain = [
            '|',
            ('l10n_latam_document_number', operator, operand),
            ('name', operator, operand)]
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = ['&', '!'] + domain[1:]
        return domain

    @api.multi
    @api.depends(
        'journal_id.sequence_id.number_next_actual',
        'l10n_latam_receiptbook_id.sequence_id.number_next_actual',
    )
    def _compute_next_number(self):
        """
        show next number only for payments without number and on draft state
        """
        for payment in self.filtered(
                lambda x: x.state == 'draft'):
            if payment.l10n_latam_receiptbook_id:
                sequence = payment.l10n_latam_receiptbook_id.sequence_id
            else:
                sequence = payment.journal_id.sequence_id
            # we must check if sequence use date ranges
            if not sequence.use_date_range:
                payment.next_number = sequence.number_next_actual
            else:
                dt = fields.Date.today()
                if self.env.context.get('ir_sequence_date'):
                    dt = self.env.context.get('ir_sequence_date')
                seq_date = self.env['ir.sequence.date_range'].search([
                    ('sequence_id', '=', sequence.id),
                    ('date_from', '<=', dt),
                    ('date_to', '>=', dt)], limit=1)
                if not seq_date:
                    seq_date = sequence._create_date_range_seq(dt)
                payment.next_number = seq_date.number_next_actual

    @api.multi
    @api.depends(
        'name',
        'l10n_latam_document_number',
        'l10n_latam_document_type_id.doc_code_prefix',
        'state'
    )
    def _compute_display_name(self):
        """
        * If document number and document type, we show them
        * Else, we show name
        """
        for rec in self:
            if (
                    rec.state == 'posted' and rec.l10n_latam_document_number and
                    rec.l10n_latam_document_type_id):
                display_name = ("%s%s" % (
                    rec.l10n_latam_document_type_id.doc_code_prefix or '',
                    rec.l10n_latam_document_number))
            else:
                display_name = rec.name
            rec.display_name = display_name

    @api.multi
    @api.constrains('company_id', 'partner_type')
    def _force_receiptbook(self):
        for rec in self:
            if not rec.l10n_latam_receiptbook_id:
                rec.l10n_latam_receiptbook_id = rec._get_receiptbook()

    @api.onchange('company_id', 'partner_type')
    def get_receiptbook(self):
        self.l10n_latam_receiptbook_id = self._get_receiptbook()

    @api.multi
    def _get_receiptbook(self):
        self.ensure_one()
        partner_type = self.partner_type or self._context.get(
            'partner_type', self._context.get('default_partner_type', False))
        receiptbook = self.env[
            'l10n_latam.payment.receiptbook'].search([
                ('partner_type', '=', partner_type),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
        return receiptbook

    @api.multi
    def post(self):
        for rec in self.filtered(
                lambda x: x.l10n_latam_receiptbook_id and not x.l10n_latam_document_number):
            if not rec.l10n_latam_receiptbook_id.sequence_id:
                raise UserError(_(
                    'Error!. Please define sequence on the receiptbook'
                    ' related documents to this payment or set the '
                    'document number.'))
            rec.l10n_latam_document_number = (
                rec.l10n_latam_receiptbook_id.sequence_id.next_by_id())
        return super(AccountPayment, self).post()

    def _get_move_vals(self, journal=None):
        vals = super(AccountPayment, self)._get_move_vals()
        vals.update({
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_latam_document_number':
            self.l10n_latam_document_number if self.payment_type != 'transfer'
            else self.name,
        })
        return vals

    @api.multi
    @api.constrains('l10n_latam_receiptbook_id', 'company_id')
    def _check_company_id(self):
        for rec in self.filtered(lambda x: x.l10n_latam_receiptbook_id and \
                x.l10n_latam_receiptbook_id.company_id != rec.company_id):
            raise ValidationError(_(
                'The company of the receiptbook and of the payment must be the'
                ' same!'))
