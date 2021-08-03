# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    check_manual_sequencing = fields.Boolean(related='journal_id.check_manual_sequencing')
    check_number = fields.Char(
        string="Check Number",
        store=True,
        readonly=False,
        copy=False,
        compute='_compute_check_number',
        inverse='_inverse_check_number',
        help="The selected journal is configured to print check numbers. If your pre-printed check paper already has numbers "
             "or if the current numbering is wrong, you can change it in the journal configuration page.",
    )
    payment_method_code = fields.Char(
        related='payment_method_line_id.code',
        help="Technical field used to adapt the interface to the payment type selected.")
    use_checkbooks = fields.Boolean(related='journal_id.use_checkbooks')
    # payment_method_id = fields.Many2one(index=True)
    checkbook_type = fields.Selection(related='checkbook_id.type')
    checkbook_id = fields.Many2one('account.checkbook', 'Checkbook', store=True, compute='_compute_checkbook', readonly=False)
    check_payment_date = fields.Date()
    check_printing_type = fields.Selection(related='checkbook_id.check_printing_type')

    @api.depends('payment_method_line_id.code', 'journal_id.use_checkbooks')
    def _compute_checkbook(self):
        with_checkbooks = self.filtered(lambda x: x.payment_method_line_id.code == 'check_printing' and x.journal_id.use_checkbooks)
        (self - with_checkbooks).checkbook_id = False
        for rec in with_checkbooks:
            checkbook = rec.journal_id.with_context(active_test=True).checkbook_ids
            rec.checkbook_id = checkbook and checkbook[0] or False

    def _create_payment_vals_from_wizard(self):
        vals = super()._create_payment_vals_from_wizard()
        vals.update({
            'checkbook_id': self.checkbook_id.id,
            'check_payment_date': self.check_payment_date,
            'check_number': self.check_number,
        })
        return vals

    @api.depends('journal_id', 'payment_method_code', 'checkbook_id')
    def _compute_check_number(self):
        for pay in self:
            if pay.journal_id.check_manual_sequencing and pay.payment_method_code == 'check_printing':
                sequence = pay.journal_id.check_sequence_id
                pay.check_number = sequence.get_next_char(sequence.number_next_actual)
            elif pay.checkbook_id.check_printing_type == 'no_print':
                pay.check_number = pay.checkbook_id.sequence_id.get_next_char(pay.checkbook_id.next_number)
            else:
                pay.check_number = False

    def _inverse_check_number(self):
        for payment in self:
            if payment.check_number:
                sequence = payment.journal_id.check_sequence_id.sudo()
                sequence.padding = len(payment.check_number)
