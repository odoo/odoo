from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    check_printing_type = fields.Selection(
        related='checkbook_id.check_printing_type',
        # [
        #     ('no_print', 'No Print'),
        #     ('print_with_number', 'Print with number'),
        #     ('print_without_number', 'Print without number'),
        #     # (pre-printed cheks numbered)
        #     # ('pre_printed_not_numbered', 'Print (pre-printed cheks not numbered)'),
        # ],
        # compute='_compute_check_printing_type',
    )
    # @api.depends(
    #     # 'journal_id.check_printing_type',
    #     'checkbook_id.check_manual_sequencing'
    # )
    # def _compute_check_printing_type(self):
    #     for rec in self:
    #         rec.check

    use_checkbooks = fields.Boolean(related='journal_id.use_checkbooks')
    checkbook_type = fields.Selection(related='checkbook_id.type')
    checkbook_id = fields.Many2one(
        'account.checkbook',
        'Checkbook',
        store=True,
        compute='_compute_checkbook',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    check_payment_date = fields.Date(
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    check_number = fields.Char(
        readonly=False,
    )

    @api.depends('payment_method_id.code', 'journal_id.use_checkbooks')
    def _compute_checkbook(self):
        with_checkbooks = self.filtered(lambda x: x.payment_method_id.code == 'check_printing' and x.journal_id.use_checkbooks)
        (self - with_checkbooks).checkbook_id = False
        for rec in with_checkbooks:
            checkbooks = rec.journal_id.with_context(active_test=True).checkbook_ids
            if rec.checkbook_id and rec.checkbook_id in checkbooks:
                continue
            rec.checkbook_id = checkbooks and checkbooks[0] or False

    # @api.depends('journal_id', 'payment_method_code')
    @api.depends('checkbook_id')
    def _compute_check_number(self):
        no_print_checkbooks = self.filtered(lambda x: x.checkbook_id.check_printing_type == 'no_print')
        for pay in no_print_checkbooks:
            pay.check_number = pay.checkbook_id.sequence_id.get_next_char(pay.checkbook_id.next_number)
        return super(AccountPayment, self - no_print_checkbooks)._compute_check_number()

    def action_post(self):
        res = super().action_post()
        # mark checks that are not printed as sent
        for payment in self.filtered(lambda x: x.checkbook_id.check_printing_type == 'no_print' and x.check_number):
            sequence = payment.checkbook_id.sequence_id
            # TODO improove this
            sequence.sudo().write({'number_next_actual': int(payment.check_number) + 1})
            payment.write({'is_move_sent': True})
        return res

    def action_mark_sent(self):
        """ Check that the recordset is valid, set the payments state to sent and call print_checks() """
        self.write({'is_move_sent': True})
        # # Since this method can be called via a client_action_multi, we need to make sure the received records are what we expect
        # self = self.filtered(lambda r: r.payment_method_id.code == 'check_printing' and r.state != 'reconciled')

        # if len(self) == 0:
        #     raise UserError(_("Payments to mark as sent must have 'Check' selected as payment method and "
        #                       "not have already been reconciled"))
        # if any(payment.journal_id != self[0].journal_id for payment in self):
        #     raise UserError(_("In order to mark as sent multiple checks at once, they must belong to the same bank journal."))

        # if not self[0].journal_id.check_manual_sequencing:
        #     # The wizard asks for the number printed on the first pre-printed check
        #     # so payments are attributed the number of the check the'll be printed on.
        #     self.env.cr.execute("""
        #           SELECT payment.id
        #             FROM account_payment payment
        #             JOIN account_move move ON movE.id = payment.move_id
        #            WHERE journal_id = %(journal_id)s
        #            AND check_number IS NOT NULL
        #         ORDER BY check_number::INTEGER DESC
        #            LIMIT 1
        #     """, {
        #         'journal_id': self.journal_id.id,
        #     })
        #     last_printed_check = self.browse(self.env.cr.fetchone())
        #     number_len = len(last_printed_check.check_number or "")
        #     next_check_number = '%0{}d'.format(number_len) % (int(last_printed_check.check_number) + 1)

        #     return {
        #         'name': _('Print Pre-numbered Checks'),
        #         'type': 'ir.actions.act_window',
        #         'res_model': 'print.prenumbered.checks',
        #         'view_mode': 'form',
        #         'target': 'new',
        #         'context': {
        #             'payment_ids': self.ids,
        #             'default_next_check_number': next_check_number,
        #         }
        #     }
        # else:
        #     self.filtered(lambda r: r.state == 'draft').action_post()
        #     return self.do_print_checks()

    @api.constrains('journal_id', 'check_number', 'checkbook_id')
    def _check_unique(self):
        for rec in self.filtered(lambda x: x.payment_method_id.code == 'check_printing' and x.check_number):
            same_checks = self.search([
                ('checkbook_id', '=', rec.checkbook_id.id),
                ('journal_id', '=', rec.journal_id.id),
                ('check_number', '=', rec.check_number),
                ('id', '!=', rec.id),
            ])
            if same_checks:
                raise ValidationError(_(
                    'Check Number (%s) must be unique per Checkbook!\n'
                    '* Check ids: %s') % (rec.check_number, same_checks.ids))
