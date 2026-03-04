from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountSpreadLine(models.Model):
    _name = "account.spread.line"
    _description = "Spread Schedule Line"
    _order = "date asc, id asc"

    spread_id = fields.Many2one("account.spread", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="spread_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="spread_id.currency_id", store=True, readonly=True)
    date = fields.Date(required=True)
    amount = fields.Monetary(required=True, currency_field="currency_id")
    move_id = fields.Many2one("account.move", readonly=True, copy=False, ondelete="set null")
    state = fields.Selection(
        [("unposted", "Unposted"), ("posted", "Posted")],
        compute="_compute_state",
        store=True,
    )

    @api.depends("move_id")
    def _compute_state(self):
        for line in self:
            line.state = "posted" if line.move_id else "unposted"

    def _counterpart_account(self):
        self.ensure_one()
        return self.spread_id.move_line_id.account_id or self.spread_id.account_id

    def _period_label(self):
        self.ensure_one()
        d = fields.Date.to_date(self.date)
        quarter = ((d.month - 1) // 3) + 1
        return f"{d.year}-Q{quarter}"

    def _create_move(self):
        self.ensure_one()
        if self.move_id:
            return self.move_id

        spread = self.spread_id
        amount = abs(self.amount)
        counterpart_account = self._counterpart_account()

        # -- QBO / ASC 606 CONTEXT ----------------------------------------
        # This method generates the journal entries that correspond
        # to the "Revenue Recognition" lines visible in QBO reports.
        # The memo field populated here ('Recognition: {name}')
        # directly addresses the "Incomplete Audit Trail" finding
        # in the January 2026 QBO analysis - every recognition
        # entry will carry service period and contract reference.
        #
        # The zero-dollar recognition entries observed for
        # Talent Assessment Partners should be investigated:
        # if a spread record exists with estimated_amount = 0,
        # this method will create $0 moves. Validate that
        # estimated_amount is always > 0 at confirmation.
        # -----------------------------------------------------------------

        memo = f"Recognition: {spread.name} - {self._period_label()}"

        if spread.spread_type == "sale":
            debit_account = spread.account_id
            credit_account = counterpart_account
        else:
            debit_account = counterpart_account
            credit_account = spread.account_id

        line_vals = [
            (
                0,
                0,
                {
                    "name": memo,
                    "account_id": debit_account.id,
                    "debit": amount,
                    "credit": 0.0,
                    "partner_id": spread.move_id.partner_id.id if spread.move_id else False,
                },
            ),
            (
                0,
                0,
                {
                    "name": memo,
                    "account_id": credit_account.id,
                    "debit": 0.0,
                    "credit": amount,
                    "partner_id": spread.move_id.partner_id.id if spread.move_id else False,
                },
            ),
        ]

        move = self.env["account.move"].create(
            {
                "journal_id": spread.journal_id.id,
                "date": self.date,
                "ref": memo,
                "company_id": spread.company_id.id,
                "line_ids": line_vals,
            }
        )
        move.action_post()
        self.move_id = move.id
        spread._update_state_from_lines()
        return move

    def action_post(self):
        for line in self:
            if line.move_id:
                raise UserError("This spread line is already posted.")
            line._create_move()
        return True

    def action_unpost(self):
        manager_group = "account_spread_cost_revenue.group_account_spread_manager"
        if not self.env.user.has_group(manager_group):
            raise UserError(_("Only spread managers can unpost recognition lines."))

        for line in self:
            if not line.move_id:
                raise UserError(_("No posted move found for this line."))

            move = line.move_id
            if move.state == "posted":
                move._reverse_moves(
                    default_values_list=[
                        {
                            "date": fields.Date.context_today(self),
                            "ref": _("Reversal of %s") % move.name,
                        }
                    ],
                    cancel=True,
                )
            else:
                move.button_cancel()
            line.move_id = False
            line.spread_id._update_state_from_lines()
        return True
