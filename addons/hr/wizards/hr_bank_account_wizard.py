from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.numbers import float_is_zero, float_round

from ..tools import debug_log as dbg


class BankAccountAllocationWizard(models.TransientModel):
    _name = "hr.bank.account.allocation.wizard"
    _description = "Bank Account Allocation Wizard"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
    )
    allocation_ids = fields.One2many(
        comodel_name="hr.bank.account.allocation.wizard.line",
        inverse_name="wizard_id",
        string="Allocations",
        readonly=False,
    )

    def _update_allocations_from_employee(self):
        self.check_singleton()
        wizard_lines = []
        distribution = self.employee_id.salary_distribution or {}
        next_seq = max(
            (entry.get("sequence", 0) for entry in distribution.values()), default=-1
        )
        for ba in self.employee_id.bank_account_ids:
            dist_entry = distribution.get(str(ba.id))
            if dist_entry:
                amount = dist_entry.get("amount")
                is_percentage = dist_entry.get("amount_is_percentage")
                sequence = dist_entry.get("sequence")
            else:
                amount = 0.0
                is_percentage = True
                next_seq += 1
                sequence = next_seq
            wizard_lines.append(
                Command.create(
                    {
                        "bank_account_id": ba.id,
                        "amount": amount,
                        "amount_type": "percentage" if is_percentage else "fixed",
                        "trusted": ba.allow_out_payment,
                        "sequence": sequence,
                    }
                )
            )
        dbg.logic.debug(
            "[allocation_wizard:%s] employee %s: %d line(s) from %d distribution "
            "entries",
            self.id,
            self.employee_id.id,
            len(wizard_lines),
            len(distribution),
        )
        self.write({"allocation_ids": wizard_lines})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        dbg.lifecycle.debug(
            "hr.bank.account.allocation.wizard.create: %s for employees %s",
            dbg.rec(records),
            records.employee_id.ids,
        )
        for wizard in records:
            wizard._update_allocations_from_employee()
        return records

    @dbg.timed
    def action_save(self):
        self.check_singleton()

        precision_digits = 2

        distribution = {}
        percentage_total = 0.0
        has_percentage = False
        seen_accounts = set()
        trust_by_account = {}

        for line in self.allocation_ids:
            bank_account = line.bank_account_id
            if bank_account.id in seen_accounts:
                raise ValidationError(
                    self.env._(
                        "Bank account %s is allocated on several lines; each"
                        " bank account can only be used once.",
                        bank_account.display_name,
                    )
                )
            seen_accounts.add(bank_account.id)

            line_amount = float_round(
                line.amount,
                precision_digits=precision_digits,
                rounding_method="DOWN",
            )
            is_percentage = line.amount_type == "percentage"
            distribution[str(bank_account.id)] = {
                "amount": line_amount,
                "sequence": line.sequence,
                "amount_is_percentage": is_percentage,
            }
            if is_percentage:
                has_percentage = True
                percentage_total += line_amount
            trust_by_account[bank_account] = line.trusted

        dbg.logic.debug(
            "[allocation_wizard:%s] %d line(s), percentage total=%s, has_percentage=%s",
            self.id,
            len(self.allocation_ids),
            percentage_total,
            has_percentage,
        )
        if has_percentage:
            if not float_is_zero(
                percentage_total - 100.0, precision_digits=precision_digits
            ):
                raise ValidationError(
                    self.env._("Total percentage allocation must equal 100%.")
                )

        trusted = self.env["res.partner.bank"]
        untrusted = self.env["res.partner.bank"]
        for account, is_trusted in trust_by_account.items():
            if is_trusted:
                trusted |= account
            else:
                untrusted |= account
        dbg.pipeline.debug(
            "[allocation_wizard:%s] trust -> %s, untrust -> %s",
            self.id,
            dbg.rec(trusted),
            dbg.rec(untrusted),
        )
        if trusted:
            trusted.sudo().write({"allow_out_payment": True})
        if untrusted:
            untrusted.sudo().write({"allow_out_payment": False})

        dbg.lifecycle.debug(
            "[allocation_wizard:%s] employee %s salary_distribution <- %s",
            self.id,
            self.employee_id.id,
            distribution,
        )
        self.employee_id.salary_distribution = distribution
