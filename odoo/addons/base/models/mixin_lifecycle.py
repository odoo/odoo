from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.models import MAGIC_COLUMNS
from odoo.tools import format_list

_debug = DebugLog(__name__)


class MixinLifecycle(models.AbstractModel):
    _name = "mixin.lifecycle"
    _description = "Document Lifecycle"

    _STATE_TRANSITIONS = {}
    _LOCKED_WRITABLE_FIELDS = {"locked"}

    locked = fields.Boolean(
        default=False,
        copy=False,
        help="A locked document cannot be modified.",
    )

    def write(self, vals):
        with _debug.perf(
            "write_guards", cr=self.env.cr, records=self, fields=len(vals)
        ):
            self._check_write_guards(vals)
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        confirmed = self.filtered(lambda r: r.state not in ("draft", "cancel"))
        if confirmed:
            _debug.logic("unlink_refused", records=confirmed, reason="not_draft_cancel")
            raise UserError(
                self.env._(
                    "Cannot delete confirmed %(desc)s. Cancel them first:\n%(records)s",
                    desc=self._description,
                    records=", ".join(confirmed.mapped("display_name")),
                ),
            )

    def _run_check_registry(self, method_names, *args):
        _debug.pipeline("check_registry", records=self, checks=",".join(method_names))
        for method_name in method_names:
            getattr(self, method_name)(*args)

    def _get_state_label(self, state):
        return dict(self._fields["state"]._description_selection(self.env)).get(
            state, state
        )

    def _prepare_confirmation_values(self):
        raise NotImplementedError(
            f"{self._name} must implement _prepare_confirmation_values()"
        )

    def _prepare_confirmation_context(self):
        return self.env.context

    def _action_confirm(self):
        pass

    def _action_cancel(self):
        self.write({"state": "cancel"})
        _debug.lifecycle("cancelled", records=self)
        return True

    def _is_lock_required(self):
        self.check_singleton()
        return False

    def _is_readonly(self):
        self.check_singleton()
        return self.state == "cancel"

    def _check_confirm_allowed(self):
        self._run_check_registry(self._get_confirm_validation_methods())

    def _get_confirm_validation_methods(self):
        return ["_check_confirm_state"]

    def _check_confirm_state(self):
        wrong_state = self.filtered(lambda r: r.state != "draft")
        if not wrong_state:
            return
        cancelled = wrong_state.filtered(lambda r: r.state == "cancel")
        confirmed = wrong_state - cancelled
        _debug.logic("confirm_refused", confirmed=confirmed, cancelled=cancelled)
        error_parts = []
        if confirmed:
            error_parts.append(
                self.env._(
                    "• Already confirmed: %s",
                    format_list(self.env, confirmed.mapped("display_name")),
                ),
            )
        if cancelled:
            error_parts.append(
                self.env._(
                    "• Cancelled: %s",
                    format_list(self.env, cancelled.mapped("display_name")),
                ),
            )
        raise UserError(
            self.env._(
                "Cannot confirm %(desc)s that are not in draft state:\n\n%(details)s",
                desc=self._description,
                details="\n".join(error_parts),
            ),
        )

    def _check_cancel_allowed(self):
        self._run_check_registry(self._get_cancel_validation_methods())

    def _get_cancel_validation_methods(self):
        return [
            "_check_cancel_state",
            "_check_cancel_except_locked",
        ]

    def _check_cancel_state(self):
        cancelled = self.filtered(lambda r: r.state == "cancel")
        if cancelled:
            _debug.logic(
                "cancel_refused", records=cancelled, reason="already_cancelled"
            )
            raise UserError(
                self.env._(
                    "The following %(desc)s are already cancelled: %(records)s",
                    desc=self._description,
                    records=format_list(self.env, cancelled.mapped("display_name")),
                ),
            )

    def _check_cancel_except_locked(self):
        locked = self.filtered("locked")
        if locked:
            _debug.logic("cancel_refused", records=locked, reason="locked")
            raise UserError(
                self.env._(
                    "Cannot cancel locked %(desc)s: %(records)s. "
                    "Please unlock them first using the 'Unlock' button.",
                    desc=self._description,
                    records=format_list(self.env, locked.mapped("display_name")),
                ),
            )

    def action_confirm(self):
        self._check_confirm_allowed()
        with _debug.perf("action_confirm", cr=self.env.cr, records=self):
            self.write(self._prepare_confirmation_values())
            self.with_context(self._prepare_confirmation_context())._action_confirm()
            self.filtered(lambda r: r._is_lock_required()).action_lock()
        _debug.lifecycle("confirmed", records=self)
        return True

    def action_cancel(self):
        self._check_cancel_allowed()
        _debug.lifecycle("cancel_allowed", records=self)
        return self._action_cancel()

    def action_draft(self):
        _debug.lifecycle("reset_to_draft", records=self)
        self.write({"state": "draft"})
        return True

    def action_lock(self):
        _debug.lifecycle("locked", records=self)
        self.write({"locked": True})
        return True

    def action_unlock(self):
        _debug.lifecycle("unlocked", records=self)
        self.write({"locked": False})
        return True

    def _check_write_guards(self, vals):
        self._run_check_registry(self._get_check_write_guards(), vals)

    def _get_check_write_guards(self):
        return [
            "_check_write_locked_order",
            "_check_write_state_frozen_fields",
            "_check_write_state_transition",
        ]

    def _get_fields_state_frozen(self):
        return {}

    def _check_write_locked_order(self, vals):
        if self.env.context.get("bypass_locked_check"):
            _debug.logic("locked_check_skipped", records=self, reason="bypass_context")
            return
        locked = self.filtered("locked")
        if not locked:
            return
        candidate = (
            set(vals) & locked._get_fields_user_editable()
        ) - self._LOCKED_WRITABLE_FIELDS
        _debug.logic(
            "locked_check",
            locked=locked,
            fields=len(vals),
            candidates=len(candidate),
        )
        if not candidate:
            return
        for record in locked:
            forbidden = {
                name
                for name in candidate
                if record._is_locked_field_changed(name, vals[name])
            }
            if forbidden:
                _debug.logic(
                    "write_refused",
                    record=record,
                    reason="locked",
                    fields=",".join(sorted(forbidden)),
                )
                raise UserError(
                    self.env._(
                        "%(record)s is locked and cannot be modified. "
                        "Unlock it first to change: %(fields)s",
                        record=record.display_name,
                        fields=record._get_field_labels(forbidden),
                    ),
                )

    def _is_locked_field_changed(self, field_name, value):
        self.check_singleton()
        field = self._fields[field_name]
        if field.type in ("many2many", "one2many"):
            return set(self[field_name].ids) != set(
                self.new({field_name: value})[field_name].ids,
            )
        return field.convert_to_cache(
            value, self, validate=False
        ) != field.convert_to_cache(self[field_name], self, validate=False)

    def _get_fields_user_editable(self):
        return {
            name
            for name, field in self._fields.items()
            if field.store
            and not field.related
            and not field.readonly
            and name not in MAGIC_COLUMNS
        }

    def _check_write_state_frozen_fields(self, vals):
        frozen_map = self._get_fields_state_frozen()
        if not frozen_map:
            return
        changed = set(vals)
        target_state = vals.get("state")
        _debug.logic(
            "frozen_fields_check",
            records=self,
            states=len(frozen_map),
            changed=len(changed),
            target=target_state,
        )
        for record in self:
            relevant_states = {record.state, target_state} - {None}
            frozen = (
                set().union(
                    *(frozen_map.get(state, set()) for state in relevant_states),
                )
                & changed
            )
            if frozen:
                _debug.logic(
                    "write_refused",
                    record=record,
                    reason="state_frozen_field",
                    fields=",".join(sorted(frozen)),
                    state=target_state or record.state,
                )
                raise UserError(
                    self.env._(
                        "You cannot modify %(fields)s on %(record)s while it is %(state)s.",
                        fields=record._get_field_labels(frozen),
                        record=record.display_name,
                        state=record._get_state_label(target_state or record.state),
                    ),
                )

    def _check_write_state_transition(self, vals):
        if "state" not in vals:
            return
        target = vals["state"]
        for record in self:
            if record.state == target:
                continue
            _debug.lifecycle(
                "state_transition", record=record, src=record.state, dst=target
            )
            if target not in self._STATE_TRANSITIONS.get(record.state, set()):
                _debug.logic(
                    "write_refused",
                    record=record,
                    reason="illegal_state_transition",
                    src=record.state,
                    dst=target,
                )
                raise UserError(
                    self.env._(
                        "Cannot move %(name)s from %(src)s to %(dst)s.",
                        name=record.display_name,
                        src=record._get_state_label(record.state),
                        dst=record._get_state_label(target),
                    ),
                )

    def _get_field_labels(self, field_names):
        return ", ".join(
            self._fields[name]._description_string(self.env) or name
            for name in sorted(field_names)
        )
