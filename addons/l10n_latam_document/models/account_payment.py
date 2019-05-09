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
    l10n_latam_use_documents = fields.Boolean(
        related='company_id.l10n_latam_use_documents',
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

    # TODO review how can we remake this
    # ... Este campo lo puedo borrar?
    # l10n_latam_document_sequence_id = fields.Many2one(
    # ... Revisar tenemos compute que dependen de el
    # l10n_latam_receiptbook_id = fields.Many2one(
    # ... este tambien dependia de reciepbook, borrar?
    # l10n_latam_document_type_id = fields.Many2one(

    @api.model
    def _search_display_name(self, operator, operand):
        domain = [
            '|',
            ('l10n_latam_document_number', operator, operand),
            ('name', operator, operand)]
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = ['&', '!'] + domain[1:]
        return domain

    # TODO Este metodo y el campo asociado lo podemos borrar?
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

    # TODO we need to define using a different sequence?
    # @api.multi
    # def post(self):
    #     for rec in self.filtered(
    #             lambda x: x.l10n_latam_receiptbook_id and not x.l10n_latam_document_number):
    #         if not rec.l10n_latam_receiptbook_id.sequence_id:
    #             raise UserError(_(
    #                 'Error!. Please define sequence on the receiptbook'
    #                 ' related documents to this payment or set the '
    #                 'document number.'))
    #         rec.l10n_latam_document_number = (
    #             rec.l10n_latam_receiptbook_id.sequence_id.next_by_id())
    #     return super(AccountPayment, self).post()

    def _get_move_vals(self, journal=None):
        vals = super(AccountPayment, self)._get_move_vals()
        vals.update({
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_latam_document_number':
            self.l10n_latam_document_number if self.payment_type != 'transfer'
            else self.name,
        })
        return vals
