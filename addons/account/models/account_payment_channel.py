from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountPaymentChannel(models.Model):
    _name = "account.payment.channel"
    _description = "Payment Channel"
    _order = "sequence, id"
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(
        compute="_compute_name",
        store=True,
        readonly=False,
    )
    sequence = fields.Integer(default=10)
    payment_method_id = fields.Many2one(
        comodel_name="account.payment.method",
        required=True,
        domain="[('payment_type', '=?', payment_type), ('id', 'in', available_payment_method_ids)]",
    )
    payment_account_id = fields.Many2one(
        comodel_name="account.account",
        copy=False,
        domain="['|', ('account_type', 'in', ('asset_current', 'liability_current')), ('id', '=', default_account_id)]",
        ondelete="restrict",
        check_company=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        index="btree_not_null",
        check_company=True,
    )
    default_account_id = fields.Many2one(related="journal_id.default_account_id")

    code = fields.Char(related="payment_method_id.code")
    payment_type = fields.Selection(related="payment_method_id.payment_type")
    company_id = fields.Many2one(related="journal_id.company_id")
    available_payment_method_ids = fields.Many2many(
        related="journal_id.available_payment_method_ids"
    )

    @api.depends("journal_id")
    @api.depends_context("hide_payment_journal_id")
    def _compute_display_name(self):
        if self.env.context.get("hide_payment_journal_id"):
            return super()._compute_display_name()
        for method in self:
            method.display_name = f"{method.name} ({method.journal_id.name})"
        return None

    @api.depends("payment_method_id.name")
    def _compute_name(self):
        for method in self:
            if not method.name:
                method.name = method.payment_method_id.name

    @api.constrains("name")
    @_debug.perf.timed
    def _check_unique_name_for_journal(self):
        self.journal_id._check_payment_channel_ids_multiplicity()

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        used_channels = self.browse(
            channel.id
            for [channel] in self.env["account.payment"]
            .sudo()
            ._read_group(
                [("payment_channel_id", "in", self.ids)], ["payment_channel_id"]
            )
        )
        unused_payment_channels = self - used_channels

        (self - unused_payment_channels).write({"journal_id": False})

        return super(AccountPaymentChannel, unused_payment_channels).unlink()
