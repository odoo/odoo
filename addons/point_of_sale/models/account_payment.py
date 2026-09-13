from odoo import api, fields, models

from ..tools import debug_log as dbg


class AccountPayment(models.Model):
    _inherit = "account.payment"

    pos_payment_method_id = fields.Many2one(
        comodel_name="pos.payment.method",
        string="POS Payment Method",
    )
    force_outstanding_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Forced Outstanding Account",
        check_company=True,
    )
    pos_session_id = fields.Many2one(
        comodel_name="pos.session",
        string="POS Session",
        index="btree_not_null",
    )

    @api.depends("force_outstanding_account_id")
    def _compute_outstanding_account_id(self):
        super()._compute_outstanding_account_id()
        for payment in self:
            if payment.force_outstanding_account_id:
                dbg.logic.debug(
                    "account.payment %s: outstanding forced to %s",
                    payment.id,
                    dbg.rec(payment.force_outstanding_account_id),
                )
                payment.outstanding_account_id = payment.force_outstanding_account_id

    def _get_payment_method_codes_to_exclude(self):
        res = super()._get_payment_method_codes_to_exclude()

        if self.env["ir.module.module"]._get("account_iso20022").state == "installed":
            sepa_ct = self.env.ref(
                "account_iso20022.account_payment_method_sepa_ct",
                raise_if_not_found=False,
            )
            if (
                sepa_ct
                and "pos_payment" in self.env.context
                and sepa_ct.code not in res
            ):
                res.append(sepa_ct.code)
        return res
