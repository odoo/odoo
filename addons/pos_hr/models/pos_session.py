from odoo import _, api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import plaintext2html

_debug = DebugLog(__name__)


class PosSession(models.Model):
    _inherit = "pos.session"
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Cashier",
        tracking=True,
        help="The employee who currently uses the cash register",
    )

    @api.model
    def _get_model_names_to_load(self, config):
        data = super()._get_model_names_to_load(config)
        if config.module_pos_hr:
            data += ["hr.employee"]
        return data

    def _set_opening_control_data(self, cashbox_value: float, notes: str):
        super()._set_opening_control_data(cashbox_value, notes)
        if author_id := self._get_message_author():
            self.message_post(
                body=plaintext2html(_("Opened register")), author_id=author_id.id
            )

    def post_close_register_message(self):
        if author_id := self._get_message_author():
            self.message_post(
                body=plaintext2html(_("Closed Register")), author_id=author_id.id
            )
            return None
        return super().post_close_register_message()

    def _get_message_author(self):
        if not self.employee_id:
            _debug.logic(
                "pos_message_author_absent",
                reason="session_has_no_cashier",
                session=self,
            )
            return None

        if related_partners := self.employee_id._get_related_partners():
            _debug.logic(
                "pos_message_author",
                by="employee_partner",
                session=self,
                employee=self.employee_id,
                partner=related_partners[0],
            )
            return related_partners[0]

        _debug.logic(
            "pos_message_author",
            by="session_user_partner",
            session=self,
            employee=self.employee_id,
            partner=self.user_id.partner_id,
        )
        return self.user_id.partner_id

    def _aggregate_payments_amounts_by_employee(self, all_payments):
        payments_by_employee = []

        for employee, payments_group in all_payments.grouped("employee_id").items():
            payments_by_employee.append(
                {
                    "id": employee.id if employee else "others",
                    "name": employee.name if employee else _("Others"),
                    "amount": sum(payments_group.mapped("amount")),
                }
            )

        _debug.pipeline(
            "pos_payments_by_employee",
            session=self,
            payments=all_payments,
            employees=len(payments_by_employee),
        )
        # Sort such that "Others" is always the last item
        return sorted(
            payments_by_employee, key=lambda p: (p["id"] == "others", p["name"])
        )

    def _aggregate_moves_by_employee(self):
        moves_per_employee = {}
        for employee, moves in (
            self.sudo().statement_line_ids.grouped("employee_id").items()
        ):
            moves_per_employee[employee.id] = {
                "id": employee.id,
                "name": employee.name,
                "amount": sum(moves.mapped("amount")),
            }

        _debug.pipeline(
            "pos_cash_moves_by_employee",
            session=self,
            employees=len(moves_per_employee),
        )
        return sorted(moves_per_employee.values(), key=lambda p: -p["amount"])

    def get_closing_control_data(self):
        data = super().get_closing_control_data()

        orders = self._get_closed_orders()
        payments = orders.payment_ids.filtered(
            lambda p: p.payment_method_id.type != "pay_later"
        )
        cash_payment_method_ids = self.payment_method_ids.filtered(
            lambda pm: pm.type == "cash"
        )
        default_cash_payment_method_id = (
            cash_payment_method_ids[0] if cash_payment_method_ids else None
        )
        default_cash_payments = (
            payments.filtered(
                lambda p: p.payment_method_id == default_cash_payment_method_id
            )
            if default_cash_payment_method_id
            else self.env["pos.payment"]
        )
        non_cash_payment_method_ids = (
            self.payment_method_ids - default_cash_payment_method_id
            if default_cash_payment_method_id
            else self.payment_method_ids
        )
        non_cash_payments_grouped_by_method_id = {
            pm.id: orders.payment_ids.filtered(
                lambda p, pm=pm: p.payment_method_id == pm
            )
            for pm in non_cash_payment_method_ids
        }

        data["default_cash_details"]["amount_per_employee"] = (
            self._aggregate_payments_amounts_by_employee(default_cash_payments)
        )
        for payment_method in data["non_cash_payment_methods"]:
            payment_method["amount_per_employee"] = (
                self._aggregate_payments_amounts_by_employee(
                    non_cash_payments_grouped_by_method_id[payment_method["id"]]
                )
            )

        data["default_cash_details"]["moves_per_employee"] = (
            self._aggregate_moves_by_employee()
        )

        _debug.pipeline(
            "pos_closing_control_by_employee",
            session=self,
            orders=orders,
            payments=payments,
            cash_payments=default_cash_payments,
            non_cash_methods=len(non_cash_payments_grouped_by_method_id),
        )
        return data

    def _prepare_account_bank_statement_line_vals(
        self, sign, amount, reason, partner_id, extras
    ):
        vals = super()._prepare_account_bank_statement_line_vals(
            sign, amount, reason, partner_id, extras
        )
        if extras.get("employee_id"):
            vals["employee_id"] = extras["employee_id"]
        return vals

    def get_cash_in_out_list(self):
        cash_in_out_list = super().get_cash_in_out_list()
        if self.config_id.module_pos_hr:
            for cash_in_out in cash_in_out_list:
                cash_move = self.env["account.bank.statement.line"].browse(
                    cash_in_out["id"]
                )
                if cash_move.employee_id:
                    cash_in_out["cashier_name"] = cash_move.partner_id.name
        return cash_in_out_list
