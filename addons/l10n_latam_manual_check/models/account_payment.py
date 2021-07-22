from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    check_printing_type = fields.Selection(
        related='checkbook_id.check_printing_type',
    )
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
            # TODO improve this
            sequence.sudo().write({'number_next_actual': int(payment.check_number) + 1})
            payment.write({'is_move_sent': True})
        return res

    def action_mark_sent(self):
        """ Check that the recordset is valid, set the payments state to sent and call print_checks() """
        self.write({'is_move_sent': True})

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

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """ Add check maturity date """
        res = super()._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)
        if self.payment_method_id.code == 'check_printing' and self.check_payment_date:
            res[0].update({'date_maturity': self.check_payment_date})
        return res
