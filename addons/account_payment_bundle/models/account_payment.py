from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):

    _inherit = "account.payment"

    is_main_payment = fields.Boolean(compute="_compute_is_main_payment", store=True)
    main_payment_id = fields.Many2one("account.payment")
    link_payment_ids = fields.One2many(comodel_name="account.payment", inverse_name="main_payment_id")
    payment_total = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_payment_total',
        store=True,
    )

    @api.depends("payment_method_line_id")
    def _compute_is_main_payment(self):
        for rec in self:
            rec.is_main_payment = rec.payment_method_line_id.payment_method_id.code == 'payment_bundle'

    @api.depends("main_payment_id")
    def _compute_available_journal_ids(self):
        super()._compute_available_journal_ids()
        for pay in self.filtered('main_payment_id'):
            bundle_journal_id = pay.company_id._get_bundle_journal(pay.payment_type)
            pay.available_journal_ids = pay.available_journal_ids.filtered(
                lambda x: x._origin.id != bundle_journal_id
            )

    @api.depends("link_payment_ids", "date", 'currency_id')
    def _compute_payment_total(self):
        for payment in self:
            payment.payment_total = 0
            for rec in payment.link_payment_ids:
                payment.payment_total += rec.currency_id._convert(
                    rec.amount,
                    payment.currency_id,
                    payment.company_id,
                    payment.date
                )

    def action_post(self):
        if self.link_payment_ids and self.payment_method_code != "payment_bundle":
            self.link_payment_ids.unlink()
        res = super(AccountPayment, self + self.link_payment_ids).action_post()
        return res

    def action_draft(self):
        res = super(AccountPayment, self + self.link_payment_ids).action_draft()
        return res

    def _bypass_journal_entry(self, write_off_line_vals):
        if not write_off_line_vals:
            return self.filtered(lambda x: x.is_main_payment)
        return self.env["account.payment"]

    def _generate_journal_entry(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        super(AccountPayment, self - self._bypass_journal_entry(write_off_line_vals))._generate_journal_entry(
            write_off_line_vals=write_off_line_vals, force_balance=force_balance, line_ids=line_ids
        )

    @api.depends("partner_id", "amount", "date", "payment_type")
    def _compute_duplicate_payment_ids(self):
        # Delete this when https://github.com/odoo/odoo/pull/210164 is merged
        # Bypass the duplicate payment check for main payments
        for rec in self:
            if rec.main_payment_id:
                rec.duplicate_payment_ids = False
            else:
                super()._compute_duplicate_payment_ids()
