import logging
from typing import Any, Self

from odoo import _, api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, config
from odoo.tools.safe_eval import safe_eval

from .ir_model_common import (
    access_mode_columns,
    check_access_mode,
    unloaded_module_clause,
    unloaded_module_scope,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrRule(models.Model):
    _name = "ir.rule"
    _description = "Record Rule"
    _order = "model_id DESC,id"
    _PERM_COLUMNS = access_mode_columns("r")
    _allow_sudo_commands = False

    name = fields.Char()
    active = fields.Boolean(
        default=True,
        help="If you uncheck the active field, it will disable the record rule without deleting it (if you delete a native record rule, it may be re-created when you reload the module).",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        index=True,
        required=True,
        ondelete="cascade",
    )
    groups = fields.Many2many(
        comodel_name="res.groups",
        relation="rule_group_rel",
        column1="rule_group_id",
        column2="group_id",
        ondelete="restrict",
    )
    domain_force = fields.Text(string="Domain")
    composition = fields.Selection(
        selection=[("grant", "Grant"), ("restrict", "Restrict")],
        default="grant",
        required=True,
        help="Grant: the rule's records are added to what the group's members may "
        "reach, and every grant rule a user matches is combined with OR. "
        "Restrict: the rule's domain is combined with AND, like a rule with no "
        "groups but only for the group's members, so no other rule can widen it.",
    )
    perm_read = fields.Boolean(
        string="Read",
        default=True,
    )
    perm_write = fields.Boolean(
        string="Write",
        default=True,
    )
    perm_create = fields.Boolean(
        string="Create",
        default=True,
    )
    perm_unlink = fields.Boolean(
        string="Delete",
        default=True,
    )

    _no_access_rights = models.Constraint(
        "CHECK (perm_read OR perm_write OR perm_create OR perm_unlink)",
        "Rule must have at least one checked access right!",
    )

    @api.model
    def _eval_context(self) -> dict[str, Any]:
        return {
            "user": self.env.user.with_context({}),
            "company_ids": self.env.companies.ids,
            "company_id": self.env.company.id,
        }

    @api.depends("groups")
    def _compute_global(self) -> None:
        for rule in self:
            rule["global"] = not rule.groups

    @api.constrains("model_id")
    def _check_model_name(self) -> None:
        if any(rule.model_id.model == self._name for rule in self):
            _debug.logic("rule_on_rules_refused", rules=self.ids)
            raise ValidationError(
                _("Rules can not be applied on the Record Rules model.")
            )

    @api.constrains("active", "domain_force", "model_id")
    def _check_domain(self) -> None:
        eval_context = self._eval_context()
        for rule in self:
            if rule.active and rule.domain_force:
                try:
                    domain = safe_eval(rule.domain_force, eval_context)
                    model = self.env[rule.model_id.model].sudo()
                    Domain(domain).check(model)
                except Exception as e:
                    _debug.logic(
                        "rule_domain_invalid",
                        rule=rule.id,
                        model=rule.model_id.model,
                        error=type(e).__name__,
                    )
                    raise ValidationError(_("Invalid domain: %s", e)) from None

    def _get_context_keys_in_domains(self) -> list[str]:
        return ["allowed_company_ids"]

    def _get_failing(self, for_records: Any, mode: str = "read") -> Self:
        Model = for_records.browse(()).sudo().with_context(active_test=False)
        eval_context = self._eval_context()

        all_rules = self._get_rules(Model._name, mode=mode).sudo()

        group_rules = all_rules.filtered(
            lambda r: (
                r.groups
                and r.composition == "grant"
                and r.groups & self.env.user.all_group_ids
            )
        )
        group_domains = Domain.OR(
            safe_eval(r.domain_force, eval_context) if r.domain_force else []
            for r in group_rules
        )
        distinct_count = len(set(for_records.ids))
        if (
            Model.search_count(group_domains & Domain("id", "in", for_records.ids))
            == distinct_count
        ):
            _debug.logic(
                "failing_rules.group_grants_cover",
                model=Model._name,
                group_rules=len(group_rules),
            )
            group_rules = self.browse(())

        def is_failing(r, ids=for_records.ids):
            dom = Domain(
                safe_eval(r.domain_force, eval_context) if r.domain_force else []
            )
            return Model.search_count(dom & Domain("id", "in", ids)) < len(set(ids))

        failing = all_rules.filtered(
            lambda r: (
                r in group_rules
                or ((not r.groups or r.composition == "restrict") and is_failing(r))
            )
        ).with_user(self.env.user)
        _debug.logic(
            "failing_rules",
            model=Model._name,
            mode=mode,
            uid=self.env.uid,
            records=distinct_count,
            rules=len(all_rules),
            failing=failing.ids,
        )
        return failing

    def _get_model_names_bound_by_rules(self, model_name: str) -> list[str]:
        model_cls = self.env.registry.get(model_name)
        root = getattr(model_cls, "_table_inheritance_root", "")
        if not root or model_cls._table == root:
            return [model_name]
        bound = [model_name] + [
            name
            for name in self.env.registry.model_names_by_inheritance_root.get(root, ())
            if self.env.registry[name]._table == root
        ]
        _debug.logic(
            "rules.bound_by_inheritance_root",
            model=model_name,
            bound=bound[1:],
        )
        return bound

    def _get_rules(self, model_name: str, mode: str = "read") -> Self:
        check_access_mode(mode)

        if self.env.su:
            _debug.logic("rules_skipped", model=model_name, mode=mode, reason="sudo")
            return self.browse(())

        sql = SQL(
            """
            SELECT r.id FROM ir_rule r
            JOIN ir_model m ON (r.model_id=m.id)
            WHERE m.model = ANY(%s) AND r.active AND %s
                AND (r.global OR r.id IN (
                    SELECT rule_group_id FROM rule_group_rel rg
                    WHERE rg.group_id = ANY(%s)
                ))
                %s
            ORDER BY r.id
            """,
            self._get_model_names_bound_by_rules(model_name),
            self._PERM_COLUMNS[mode],
            list(self.env.user._get_group_ids()),
            self._get_clause_for_unloaded_module_rules(),
        )
        rules = self.browse(v for (v,) in self.env.execute_query(sql))
        _debug.perf.count(
            "rules_fetched",
            model=model_name,
            mode=mode,
            uid=self.env.uid,
            rules=len(rules),
        )
        return rules

    def _get_clause_for_unloaded_module_rules(self) -> SQL:
        return unloaded_module_clause(self.env, "ir.rule", "r")

    def _get_unloaded_module_scope(self) -> tuple[int, str | None] | None:
        return unloaded_module_scope(self.env)

    @api.model
    @tools.conditional(
        "xml" not in config["dev_mode"],
        tools.ormcache(
            "self.env.uid",
            "self.env.su",
            "model_name",
            "mode",
            "tuple(self._get_context_values_in_domains())",
            "self._get_unloaded_module_scope()",
        ),
    )
    def _get_domain_accessible_records(
        self, model_name: str, mode: str = "read"
    ) -> Domain:
        model = self.env[model_name]

        global_domains: list[Domain] = []
        for parent_model_name, parent_field_name in model._inherits.items():
            if not model._inherits_rules or not model._fields[parent_field_name].store:
                continue
            if domain := self._get_domain_accessible_records(parent_model_name, mode):
                _debug.logic(
                    "rule_domain_inherited",
                    model=model_name,
                    parent=parent_model_name,
                    field=parent_field_name,
                )
                global_domains.append(Domain(parent_field_name, "any", domain))

        rules = self._get_rules(model_name, mode=mode)
        if not rules:
            _debug.logic(
                "rule_domain_none", model=model_name, mode=mode, uid=self.env.uid
            )
            return Domain.AND(global_domains).optimize(model)

        eval_context = self._eval_context()
        user_groups = self.env.user.all_group_ids
        group_domains: list[Domain] = []
        for rule in rules.sudo():
            if rule.groups and not (rule.groups & user_groups):
                _debug.logic(
                    "rule_skipped", rule=rule.id, model=model_name, reason="no_group"
                )
                continue
            dom = (
                Domain(safe_eval(rule.domain_force, eval_context))
                if rule.domain_force
                else Domain.TRUE
            )
            if rule.groups and rule.composition == "grant":
                group_domains.append(dom)
            else:
                global_domains.append(dom)

        if group_domains:
            global_domains.append(Domain.OR(group_domains))
        _debug.logic(
            "rule_domain_computed",
            model=model_name,
            mode=mode,
            uid=self.env.uid,
            rules=len(rules),
            global_domains=len(global_domains),
            group_domains=len(group_domains),
        )
        return Domain.AND(global_domains).optimize(model)

    def _get_context_values_in_domains(self) -> Any:
        for k in self._get_context_keys_in_domains():
            v = self.env.context.get(k)
            if isinstance(v, list):
                v = tuple(v)
            yield v

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", count=len(self))
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)
        _debug.lifecycle("create", count=len(res))
        self.env.flush_all()
        self.env.registry.clear_cache()
        return res

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        res = super().write(vals)
        self.env.flush_all()
        self.env.registry.clear_cache()
        return res

    def _prepare_access_error(self, operation: str, records: Any) -> AccessError:
        _logger.info(
            "Access Denied by record rules for operation: %s on record ids: %r, uid: %s, model: %s",
            operation,
            records.ids[:6],
            self.env.uid,
            records._name,
        )
        self = self.with_context(self.env.user.context_get())

        model = records._name
        description = self.env["ir.model"]._get(model).name or model
        operations = {
            "read": _("read"),
            "write": _("write"),
            "create": _("create"),
            "unlink": _("unlink"),
        }
        user_description = f"{self.env.user.name} (id={self.env.user.id})"
        operation_error = _(
            "Uh-oh! Looks like you have stumbled upon some top-secret records.\n\n"
            "Sorry, %(user)s doesn't have '%(operation)s' access to:",
            user=user_description,
            operation=operations.get(operation, operation),
        )
        failing_model = _(
            "- %(description)s (%(model)s)",
            description=description,
            model=model,
        )

        resolution_info = _(
            "If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."
        )

        rules = self._get_failing(records, mode=operation).sudo()

        display_records = records[:6].sudo()
        company_related = any("company_id" in (r.domain_force or "") for r in rules)
        _debug.logic(
            "access_error.prepared",
            model=model,
            operation=operation,
            uid=self.env.uid,
            records=len(records),
            rules=len(rules),
            company_related=company_related,
        )

        def get_record_description(rec):
            if (
                company_related
                and "company_id" in rec
                and rec.company_id in self.env.user.company_ids
            ):
                return f"{description}, {rec.display_name} ({model}: {rec.id}, company={rec.company_id.display_name})"
            return f"{description}, {rec.display_name} ({model}: {rec.id})"

        context = None
        if company_related:
            resolution_info, context = self._get_company_resolution_info(
                display_records, resolution_info
            )

        if (
            not self.env.user.has_group("base.group_no_one")
            or not self.env.user._is_internal()
        ):
            _debug.logic(
                "access_error.terse", uid=self.env.uid, reason="not_debug_user"
            )
            msg = f"{operation_error}\n{failing_model}\n\n{resolution_info}"
        else:
            failing_records = "\n".join(
                f"- {get_record_description(rec)}" for rec in display_records
            )
            rules_description = "\n".join(f"- {rule.name}" for rule in rules)
            failing_rules = _("Blame the following rules:\n%s", rules_description)
            msg = f"{operation_error}\n{failing_records}\n\n{failing_rules}\n\n{resolution_info}"

        records.invalidate_recordset()

        exception = AccessError(msg)
        if context:
            exception.context = context
        return exception

    def _get_company_resolution_info(
        self, display_records: Any, resolution_info: str
    ) -> tuple[str, dict | None]:
        context = None
        suggested_companies = display_records._get_redirect_suggested_company()
        _debug.logic(
            "access_error_company_hint",
            uid=self.env.uid,
            suggested=len(suggested_companies) if suggested_companies else 0,
            reachable=bool(suggested_companies)
            and suggested_companies in self.env.user.company_ids,
        )
        if suggested_companies and len(suggested_companies) != 1:
            resolution_info += _(
                "\n\nNote: this might be a multi-company issue. Switching company may help - in Odoo, not in real life!"
            )
        elif suggested_companies and suggested_companies in self.env.user.company_ids:
            context = {
                "suggested_company": {
                    "id": suggested_companies.id,
                    "display_name": suggested_companies.display_name,
                }
            }
            resolution_info += _(
                "\n\nThis seems to be a multi-company issue, you might be able to access the record by switching to the company: %s.",
                suggested_companies.display_name,
            )
        elif suggested_companies:
            resolution_info += _(
                "\n\nThis seems to be a multi-company issue, but you do not have access to the proper company to access the record anyhow."
            )
        return resolution_info, context


global_ = fields.Boolean(
    compute="_compute_global",
    store=True,
    help="If no group is specified the rule is global and applied to everyone",
)
setattr(IrRule, "global", global_)
global_.__set_name__(IrRule, "global")
