# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import UTC, datetime

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_VALID_ACTION_TYPES = frozenset({"line_void", "quantity_decrease"})


class PosSession(models.Model):
    _inherit = "pos.session"

    def _l10n_ph_parse_transaction_date(self, payload):
        """Parse and normalize a transaction date from the POS payload to a UTC string."""
        transaction_date = payload.get("transaction_date")
        if not transaction_date:
            return fields.Datetime.to_string(fields.Datetime.now())
        if isinstance(transaction_date, str) and transaction_date.endswith("Z"):
            transaction_date = f"{transaction_date[:-1]}+00:00"
        try:
            parsed = (
                datetime.fromisoformat(transaction_date)
                if isinstance(transaction_date, str)
                else fields.Datetime.to_datetime(transaction_date)
            )
            if not parsed:
                return fields.Datetime.to_string(fields.Datetime.now())
            if parsed.tzinfo:
                parsed = parsed.astimezone(UTC).replace(tzinfo=None)
            return fields.Datetime.to_string(parsed)
        except (TypeError, ValueError):
            _logger.warning(
                "l10n_ph_pos: could not parse transaction_date %r, using now()",
                transaction_date,
            )
            return fields.Datetime.to_string(fields.Datetime.now())

    def _l10n_ph_validate_audit_action_payload(
        self,
        payload,
        *,
        require_approver=True,
    ):
        reason = (payload.get("reason") or "").strip()
        passcode = (payload.get("passcode") or "").strip()
        approver_id = payload.get("approver_id")
        action_type = payload.get("action_type") or "line_void"
        if action_type not in _VALID_ACTION_TYPES:
            raise UserError(self.env._("Unsupported audit action."))

        if require_approver and not passcode and not approver_id:
            raise UserError(
                self.env._(
                    "A passcode or approver is required to log the audit action.",
                ),
            )
        if not payload.get("product_id"):
            raise UserError(self.env._("A product is required to log a voided line."))
        return action_type, reason, passcode

    def _l10n_ph_get_audit_approver(self, payload, passcode):
        allowed_employees = self._l10n_ph_get_void_authorized_employees().sudo()
        approver_id = payload.get("approver_id")
        if approver_id:
            approver = allowed_employees.filtered(lambda emp: emp.id == approver_id)
            if not approver:
                raise UserError(
                    self.env._("The selected approver is not allowed for this action."),
                )
            return approver[0]

        matching_approvers = allowed_employees.filtered(
            lambda emp: emp.pin and emp.pin == passcode,
        )
        if not matching_approvers:
            raise UserError(self.env._("Invalid passcode for Basic/Advanced rights."))
        if len(matching_approvers) > 1:
            raise UserError(
                self.env._(
                    "The passcode matches multiple employees. Use unique employee PINs.",
                ),
            )
        return matching_approvers[0]

    def _l10n_ph_get_void_authorized_employees(self):
        """Return employees authorized to approve line void actions (basic + advanced)."""
        self.ensure_one()
        config = self.config_id.sudo()
        all_employees = (
            self.env["hr.employee"]
            .sudo()
            .search(config._employee_domain(self.user_id.id))
        )
        basic_employees = config.basic_employee_ids or (
            all_employees - config.minimal_employee_ids - config.advanced_employee_ids
        )
        return basic_employees | config.advanced_employee_ids

    def _l10n_ph_build_audit_remark(self, action_type, payload):
        if action_type != "quantity_decrease":
            return self.env._("Line was voided.")

        old_quantity = payload.get("old_quantity")
        new_quantity = payload.get("new_quantity")
        if old_quantity is None or new_quantity is None:
            return self.env._("Quantity was reduced.")
        return self.env._(
            "Quantity reduced from %(old_qty)s to %(new_qty)s.",
            old_qty=old_quantity,
            new_qty=new_quantity,
        )

    def _l10n_ph_get_audit_cashier(self, payload):
        """Resolve the cashier employee for audit logging from the payload context."""
        HrEmployee = self.env["hr.employee"].sudo()

        cashier_id = payload.get("cashier_employee_id")
        if cashier_id:
            cashier = HrEmployee.browse(cashier_id).exists()
            if cashier:
                return cashier

        user_id = payload.get("cashier_user_id")
        if user_id:
            employee = self.env["res.users"].sudo().browse(user_id).employee_id
            if employee:
                return employee

        cashier = self.employee_id.sudo() or self.user_id.employee_id.sudo()
        if not cashier:
            raise UserError(
                self.env._("Could not determine the cashier for the audit action."),
            )
        return cashier

    def l10n_ph_log_order_line_action(self, payload):
        self.ensure_one()
        cashier = self._l10n_ph_get_audit_cashier(payload)
        allow_self = bool(cashier and cashier.l10n_ph_pos_allow_self_line_void)
        action_type, reason, passcode = self._l10n_ph_validate_audit_action_payload(
            payload,
            require_approver=not allow_self,
        )
        action_uid = (payload.get("action_uid") or "").strip()
        if action_uid:
            existing_log = (
                self.env["l10n_ph.pos.line.void"]
                .sudo()
                .search(
                    [("source_uid", "=", action_uid)],
                    limit=1,
                )
            )
            if existing_log:
                return {
                    "void_counter": self.config_id.l10n_ph_void_counter,
                    "approver_name": existing_log.approver_employee_id.name,
                    "action_type": action_type,
                }

        if allow_self:
            approver = cashier
        else:
            approver = self._l10n_ph_get_audit_approver(payload, passcode)
        transaction_date = self._l10n_ph_parse_transaction_date(payload)
        audit_remark = self._l10n_ph_build_audit_remark(action_type, payload)

        self.env["l10n_ph.pos.line.void"].sudo().create(
            {
                "transaction_date": transaction_date,
                "approver_badge_number": approver.barcode,
                "approver_employee_id": approver.id,
                "cashier_badge_number": cashier.barcode,
                "cashier_employee_id": cashier.id,
                "config_id": self.config_id.id,
                "session_id": self.id,
                "reason": reason,
                "remark": audit_remark,
                "product_id": payload.get("product_id"),
                "description": payload.get("description"),
                "quantity": payload.get("quantity") or 0,
                "unit_price": payload.get("unit_price") or 0,
                "net_amount": payload.get("net_amount") or 0,
                "user_id": self.env.user.id,
                "source_uid": action_uid or False,
            },
        )

        void_counter = self.config_id.l10n_ph_void_counter
        if action_type == "line_void":
            self.env.cr.execute(
                SQL(
                    """
                UPDATE pos_config
                   SET l10n_ph_void_counter = COALESCE(l10n_ph_void_counter, 0) + 1
                 WHERE id = %s RETURNING l10n_ph_void_counter
                """,
                    self.config_id.id,
                ),
            )
            void_counter = self.env.cr.fetchone()[0]
            self.config_id.invalidate_recordset(["l10n_ph_void_counter"])
            self.config_id._compute_local_data_integrity()
        return {
            "void_counter": void_counter,
            "approver_name": approver.name,
            "action_type": action_type,
        }
