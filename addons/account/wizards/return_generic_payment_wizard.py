from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountReturnGenericPaymentWizard(models.TransientModel):
    _name = "account.return.payment.wizard"
    _description = "Returns Generic Payment Wizard"

    company_id = fields.Many2one(comodel_name="res.company")
    # compute_sudo=False on both: a related field is privileged by default
    # (coding_guidelines.rst 10.5), and partner_bank_id is a plain many2one the user
    # sets, so the default would hand back the IBAN of any bank account in the
    # database -- including ones the reader's record rules hide.
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="partner_bank_id.partner_id",
        compute_sudo=False,
    )
    acc_number = fields.Char(
        related="partner_bank_id.acc_number",
        string="IBAN",
        compute_sudo=False,
    )
    # No check_company= here on purpose: this model does not set _check_company_auto,
    # so the flag would enforce nothing while reading as though it did. The reader's
    # own record rules are what scope this now, via compute_sudo=False above.
    partner_bank_id = fields.Many2one(comodel_name="res.partner.bank")
    communication = fields.Char(compute="_compute_communication")

    amount_to_pay = fields.Monetary(
        compute="_compute_amount_to_pay",
        store=True,
        readonly=False,
    )
    is_recoverable = fields.Boolean(
        compute="_compute_is_recoverable",
        readonly=False,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="return_id.amount_to_pay_currency_id",
    )
    return_id = fields.Many2one(
        comodel_name="account.return",
        required=True,
    )

    @_debug.perf.timed
    def _generate_communication(self):
        return False

    @api.depends("return_id")
    def _compute_amount_to_pay(self):
        for wizard in self:
            wizard.amount_to_pay = wizard.return_id.total_amount_to_pay

    @api.depends("amount_to_pay")
    def _compute_is_recoverable(self):
        for wizard in self:
            result = wizard.currency_id.compare_amounts(wizard.amount_to_pay, 0)
            wizard.is_recoverable = result in (-1, 0)

    @api.depends("company_id")
    def _compute_communication(self):
        for wizard in self:
            wizard.communication = wizard._generate_communication()

    @_debug.perf.timed
    def action_mark_as_paid(self):
        _debug.lifecycle("action_mark_as_paid", records=self)
        self.check_singleton()
        return self.return_id._action_finalize_payment()

    @_debug.perf.timed
    def action_send_email_instructions(self):
        _debug.lifecycle("action_send_email_instructions", records=self)
        self.check_singleton()
        template = self.env.ref(
            "account.email_template_generic_tax_instructions",
            raise_if_not_found=False,
        )
        return self.return_id.action_send_email_instructions(self, template)
