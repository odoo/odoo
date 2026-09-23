import ast
import logging
import typing
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from typing import Any, Self

from odoo import _, api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain, DomainCondition
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, frozendict
from odoo.tools.safe_eval import safe_eval, time

from .ir_model_common import (
    ACCESS_ERROR_GROUPS,
    ACCESS_ERROR_HEADER,
    ACCESS_ERROR_NOGROUP,
    ACCESS_ERROR_RESOLUTION,
    ACCESS_MODES,
    unloaded_module_domain,
    unloaded_module_scope,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

CRUD_SELECTION = {
    "crud": "Create, Read, Update, Delete",
    "cru": "Create, Read, Update",
    "crd": "Create, Read, Delete",
    "cud": "Create, Update, Delete",
    "rud": "Read, Update, Delete",
    "cr": "Create, Read",
    "cu": "Create, Update",
    "cd": "Create, Delete",
    "ru": "Read, Update",
    "rd": "Read, Delete",
    "ud": "Update, Delete",
    "c": "Create",
    "r": "Read",
    "u": "Update",
    "d": "Delete",
}
OPERATION_LETTER = {"create": "c", "read": "r", "write": "u", "unlink": "d"}
NON_STANDARD_MODULES = ("__export__", "__custom__", "studio_customization")
GROUP_TESTS = frozenset(
    {
        "all_group_ids",
        "group_ids",
        "groups_id",
        "has_group",
        "has_groups",
        "_has_group",
        "_get_group_ids",
    }
)


class AccessInfo(typing.NamedTuple):
    id: int
    group_id: int
    kind: str
    guard_scope: str
    operation: str
    domain: Domain | str


def domain_group_tests(domain: str) -> list[str]:
    # a domain that tests the principal's groups can make a group take records
    # away; the row's group is where membership is stated
    try:
        tree = ast.parse(domain.strip(), mode="eval")
    except SyntaxError:
        return []
    return sorted(
        {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr in GROUP_TESTS
        }
    )


def _conditions_with_models(
    model: models.BaseModel, domain: Domain
) -> Iterator[tuple[models.BaseModel, DomainCondition]]:
    for condition in domain.iter_conditions():
        *path, last = condition.field_expr.split(".")
        owner = model
        for name in path:
            field = owner._fields.get(name)
            if field is None or not field.relational:
                break
            owner = owner.env[field.comodel_name]
        else:
            condition = DomainCondition(last, condition.operator, condition.value)
            yield owner, condition
            field = owner._fields.get(last)
            value = condition.value
            if (
                field is not None
                and field.relational
                and condition.operator in ("any", "not any", "any!", "not any!")
                and isinstance(value, (Domain, list, tuple))
            ):
                yield from _conditions_with_models(
                    owner.env[field.comodel_name], Domain(value)
                )


def access_edges(model: models.BaseModel, domain: Domain) -> Iterator[tuple[str, str]]:
    for owner, condition in _conditions_with_models(model, domain):
        if condition.operator != "access":
            continue
        field = owner._fields.get(condition.field_expr)
        if condition.value not in OPERATION_LETTER:
            raise ValueError(
                f"The 'access' operator takes one of {ACCESS_MODES}, "
                f"not {condition.value!r}"
            )
        if field is not None and field.name == "id":
            yield owner._name, condition.value
        elif field is not None and field.is_many2one:
            yield field.comodel_name, condition.value
        else:
            raise ValueError(
                f"The 'access' operator works only for many2one and 'id' fields, "
                f"not {owner._name}.{condition.field_expr}"
            )


def without_access_conditions(domain: Domain) -> Domain:
    # a domain's own validity, read without resolving what other accesses
    # allow: those rows are checked on their own
    def skip(condition: DomainCondition) -> Domain:
        if condition.operator == "access":
            return DomainCondition(condition.field_expr, "!=", False)
        if condition.operator in ("any", "not any", "any!", "not any!") and isinstance(
            condition.value, (Domain, list, tuple)
        ):
            return DomainCondition(
                condition.field_expr,
                condition.operator,
                without_access_conditions(Domain(condition.value)),
            )
        return condition

    return domain.map_conditions(skip)


def find_access_cycle(
    edges: Mapping[tuple[str, str], Iterable[tuple[str, str]]],
) -> list[tuple[str, str]] | None:
    done: set[tuple[str, str]] = set()
    for start in list(edges):
        if start in done:
            continue
        path = [start]
        stack = [iter(edges.get(start, ()))]
        while stack:
            target = next(stack[-1], None)
            if target is None:
                stack.pop()
                done.add(path.pop())
            elif target in path:
                return path[path.index(target) :] + [target]
            elif target not in done:
                path.append(target)
                stack.append(iter(edges.get(target, ())))
    return None


class IrAccess(models.Model):
    _name = "ir.access"
    _description = "Access"
    _order = "model_id, group_id, id"
    _allow_sudo_commands = False

    name = fields.Char(required=True)
    active = fields.Boolean(
        default=True,
        help="Only active accesses are taken into account when checking access rights.",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        index=True,
        required=True,
        ondelete="cascade",
    )
    group_id = fields.Many2one(
        comodel_name="res.groups",
        index=True,
        required=True,
        ondelete="cascade",
        help="The group the row is for. A guard scoped to everyone binds every "
        "principal whatever its group; Everyone is the group of every user.",
    )
    kind = fields.Selection(
        selection=[("permission", "Permission"), ("guard", "Guard")],
        required=True,
        help="A permission adds the records of its domain to what its group may "
        "reach; the permissions a principal holds are combined with OR. A guard "
        "is combined with AND and cannot be widened by any permission.",
    )
    guard_scope = fields.Selection(
        selection=[("everyone", "Everyone"), ("members", "Members of the group")],
        default="everyone",
        required=True,
        help="Whom a guard binds: every principal, or only the members of its group.",
    )
    operation = fields.Selection(
        selection=list(CRUD_SELECTION.items()),
        required=True,
        help="Which operation(s) this access applies to, a subset of 'crud'.",
    )
    domain = fields.Char(
        help="The operations are allowed only on the records in this domain.",
    )
    for_read = fields.Boolean(
        string="Read",
        compute="_compute_for_operations",
        inverse="_inverse_for_operations",
        store=True,
    )
    for_write = fields.Boolean(
        string="Update",
        compute="_compute_for_operations",
        inverse="_inverse_for_operations",
        store=True,
    )
    for_create = fields.Boolean(
        string="Create",
        compute="_compute_for_operations",
        inverse="_inverse_for_operations",
        store=True,
    )
    for_unlink = fields.Boolean(
        string="Delete",
        compute="_compute_for_operations",
        inverse="_inverse_for_operations",
        store=True,
    )
    is_standard = fields.Boolean(
        compute="_compute_is_standard",
        search="_search_is_standard",
        compute_sudo=True,
        help="Whether the access is defined by a module.",
    )
    note = fields.Html()

    @api.depends("operation")
    def _compute_for_operations(self) -> None:
        for access in self:
            letters = access.operation or ""
            for operation, letter in OPERATION_LETTER.items():
                access[f"for_{operation}"] = letter in letters

    def _inverse_for_operations(self) -> None:
        for access in self:
            access.operation = self._operation_of(access) or "r"

    @staticmethod
    def _operation_of(values: Any) -> str:
        return "".join(
            letter
            for operation, letter in OPERATION_LETTER.items()
            if values[f"for_{operation}"]
        )

    def _compute_is_standard(self) -> None:
        xids = self._get_external_ids()
        for access in self:
            access.is_standard = any(
                not xid.startswith(NON_STANDARD_MODULES) for xid in xids[access.id]
            )

    def _search_is_standard(self, operator: str, value: Any) -> Domain:
        if operator not in ("in", "not in"):
            return NotImplemented
        standard = SQL(
            "SELECT d.res_id FROM ir_model_data d "
            "WHERE d.model = %s AND d.module != ALL(%s)",
            self._name,
            list(NON_STANDARD_MODULES),
        )
        positive = (True in value) == (operator == "in")
        return Domain("id", "in" if positive else "not in", standard)

    @staticmethod
    def _operation_letter(operation: str) -> str:
        if operation not in OPERATION_LETTER:
            raise ValueError(
                f"Invalid access operation {operation!r}: expected one of {ACCESS_MODES}."
            )
        return OPERATION_LETTER[operation]

    @api.constrains("model_id", "domain")
    def _check_model_name(self) -> None:
        if any(
            access.model_id.model == self._name and access.domain for access in self
        ):
            raise ValidationError(
                _(
                    "Accesses with a domain can not be applied on the model Access itself."
                )
            )

    @api.constrains("active", "domain", "model_id", "operation")
    def _check_domain(self) -> None:
        eval_context = self._eval_context()
        for access in self:
            if not (access.active and access.domain):
                continue
            if tests := domain_group_tests(access.domain):
                raise ValidationError(
                    _(
                        "The domain of %(access)s tests the user's groups (%(tests)s). "
                        "Group membership is what the access's group states: a domain "
                        "that reads it lets a group take records away. Put the rows on "
                        "the groups instead.",
                        access=access.name,
                        tests=", ".join(tests),
                    )
                )
            model = self.env[access.model_id.model].sudo()
            try:
                domain = Domain(safe_eval(access.domain, eval_context))
                list(access_edges(model, domain))
                without_access_conditions(domain).check(model)
            except Exception as e:
                _debug.logic(
                    "access_domain_invalid",
                    access=access.id,
                    model=model._name,
                    error=type(e).__name__,
                )
                raise ValidationError(
                    _(
                        "Invalid domain %(domain)s: %(error)s",
                        domain=access.domain,
                        error=e,
                    )
                ) from None
        # a new cycle goes through a written row's 'access' condition
        if any("access" in (access.domain or "") for access in self):
            self._check_access_graph()

    def _check_access_graph(self) -> None:
        rows = (
            self.sudo().with_context(active_test=False).search([("active", "=", True)])
        )
        cycle = self._access_cycle(self._access_infos(rows))
        if cycle:
            raise ValidationError(self._access_cycle_message(cycle))

    @staticmethod
    def _access_cycle_message(cycle: list[tuple[str, str]]) -> str:
        return _(
            "The 'access' conditions of the accesses form a cycle: %(cycle)s. "
            "A record's access cannot depend on itself; break the cycle with a "
            "domain that does not go through the 'access' operator.",
            cycle=" -> ".join(f"{model}.{operation}" for model, operation in cycle),
        )

    def _access_cycle(
        self, infos: Mapping[str, tuple[AccessInfo, ...]]
    ) -> list[tuple[str, str]] | None:
        registry = self.env.registry
        edges: defaultdict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
        eval_context = None
        for model_name in registry.models:
            model_class = registry[model_name]
            if model_class._abstract or not model_class._inherits_rules:
                continue
            for parent_model_name in model_class._inherits:
                for operation in OPERATION_LETTER:
                    edges[model_name, operation].add((parent_model_name, operation))
        for model_name, rows in infos.items():
            model = self.env[model_name].sudo()
            for row in rows:
                domain = row.domain
                if not isinstance(domain, Domain):
                    if eval_context is None:
                        eval_context = self._eval_context()
                    try:
                        domain = Domain(safe_eval(domain, eval_context))
                    except Exception:
                        _logger.warning(
                            "Access %s: its domain does not evaluate",
                            row.id,
                            exc_info=True,
                        )
                        continue
                try:
                    targets = set(access_edges(model, domain))
                except ValueError:
                    continue
                for operation, letter in OPERATION_LETTER.items():
                    if letter in row.operation:
                        edges[model_name, operation].update(targets)
        return find_access_cycle(edges)

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        everyone = None
        for vals in vals_list:
            if "operation" not in vals and (
                operation := self._operation_of(
                    {f"for_{op}": vals.get(f"for_{op}") for op in OPERATION_LETTER}
                )
            ):
                vals["operation"] = operation
            if not vals.get("group_id"):
                if everyone is None:
                    everyone = self.env.ref("base.group_everyone")
                _logger.warning(
                    "Access %s has no group: it is given to %s.",
                    vals.get("name"),
                    everyone.name,
                )
                vals["group_id"] = everyone.id
        self.env.flush_all()
        accesses = super().create(vals_list)
        _debug.lifecycle("create", count=len(accesses))
        self._clear_access_caches()
        return accesses

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        self.env.flush_all()
        result = super().write(vals)
        self._clear_access_caches()
        return result

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", count=len(self))
        self.env.flush_all()
        result = super().unlink()
        self._clear_access_caches()
        return result

    def _clear_access_caches(self) -> None:
        self.env.flush_all()
        self.env.invalidate_all()
        self.env.registry.clear_cache("stable")

    def customize(self) -> dict[str, Any]:
        self.check_singleton()
        if self.is_standard:
            access = self.copy()
            self.active = False
        else:
            access = self
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": self._name,
            "res_id": access.id,
        }

    def _eval_context(self) -> dict[str, Any]:
        return {
            "user": self.env.user.with_context({}),
            "time": time,
            "company_ids": self.env.companies.ids,
            "company_id": self.env.company.id,
        }

    def _get_unloaded_module_scope(self) -> tuple[int, str | None] | None:
        return unloaded_module_scope(self.env)

    def _policy_signature(self) -> tuple:
        env = self.env
        companies = env.context.get("allowed_company_ids")
        return (
            env.uid,
            env.user._get_group_ids(),
            tuple(companies) if companies else (),
            unloaded_module_scope(env),
        )

    def _access_infos(self, accesses: Self) -> dict[str, tuple[AccessInfo, ...]]:
        result: defaultdict[str, list[AccessInfo]] = defaultdict(list)
        registry = self.env.registry
        for access in accesses:
            model_name = access.model_id.model
            if model_name not in registry:
                continue
            domain: Domain | str = (access.domain or "").strip()
            try:
                domain = Domain(ast.literal_eval(domain)) if domain else Domain.TRUE
            except ValueError, SyntaxError:
                _debug.logic(
                    "access_domain_dynamic", access=access.id, model=model_name
                )
            result[model_name].append(
                AccessInfo(
                    access.id,
                    access.group_id.id,
                    access.kind,
                    access.guard_scope,
                    access.operation,
                    domain,
                )
            )
        return {model_name: tuple(infos) for model_name, infos in result.items()}

    @api.model
    @tools.ormcache("self._get_unloaded_module_scope()", cache="stable")
    def _get_all_access(self) -> frozendict:
        accesses = (
            self.sudo()
            .with_context(active_test=False)
            .search(
                Domain("active", "=", True)
                & unloaded_module_domain(self.env, self._name),
                order="id",
            )
        )
        infos = self._access_infos(accesses)
        if cycle := self._access_cycle(infos):
            raise ValueError(self._access_cycle_message(cycle))
        _debug.perf.count("accesses_loaded", rows=len(accesses), models=len(infos))
        return frozendict(infos)

    def _get_groups_with_access(self, model_name: str, operation: str) -> Any:
        letter = self._operation_letter(operation)
        group_ids = {
            row.group_id
            for row in self._get_all_access().get(model_name, ())
            if row.kind == "permission" and letter in row.operation
        }
        return self.env["res.groups"].sudo().browse(sorted(group_ids))

    def _make_model_access_error(self, model_name: str, operation: str) -> AccessError:
        _logger.info(
            "Access Denied by accesses for operation: %s, uid: %s, model: %s",
            operation,
            self.env.uid,
            model_name,
        )
        operation_error = str(ACCESS_ERROR_HEADER[operation]) % {
            "document_kind": self.env["ir.model"]._get(model_name).name or model_name,
            "document_model": model_name,
        }
        groups = self._get_groups_with_access(model_name, operation)
        if groups:
            group_info = str(ACCESS_ERROR_GROUPS) % {
                "groups_list": "\n".join(f"\t- {g.display_name}" for g in groups)
            }
        else:
            group_info = str(ACCESS_ERROR_NOGROUP)
        return AccessError(
            "\n\n".join([operation_error, group_info, str(ACCESS_ERROR_RESOLUTION)])
        )

    def _make_record_access_error(self, records: Any, operation: str) -> AccessError:
        _logger.info(
            "Access Denied by accesses for operation: %s on record ids: %r, uid: %s, model: %s",
            operation,
            records.ids[:6],
            self.env.uid,
            records._name,
        )
        self = self.with_context(self.env.user.context_get())
        model_name = records._name
        description = self.env["ir.model"]._get(model_name).name or model_name
        operation_names = {
            "read": _("read"),
            "write": _("write"),
            "create": _("create"),
            "unlink": _("unlink"),
        }
        operation_error = _(
            "Uh-oh! Looks like you have stumbled upon some top-secret records.\n\n"
            "Sorry, %(user)s doesn't have '%(operation)s' access to:",
            user=f"{self.env.user.name} (id={self.env.uid})",
            operation=operation_names[operation],
        )
        failing_model = _(
            "- %(description)s (%(model)s)", description=description, model=model_name
        )
        resolution_info = _(
            "If you really, really need access, perhaps you can win over your "
            "friendly administrator with a batch of freshly baked cookies."
        )
        accesses = self._get_failed_accesses(records, operation)
        display_records = records[:6].sudo()
        company_related = any("company_id" in (a.domain or "") for a in accesses)
        context = None
        if company_related:
            resolution_info, context = self.env["ir.rule"]._get_company_resolution_info(
                display_records, resolution_info
            )
        if (
            self.env.user.has_group("base.group_no_one")
            and self.env.user._is_internal()
        ):
            failing_records = "\n".join(
                f"- {description}, {record.display_name} ({model_name}: {record.id})"
                for record in display_records
            )
            blame = "\n".join(f"- {access.name}" for access in accesses)
            message = (
                f"{operation_error}\n{failing_records}\n\n"
                f"{_('Blame the following accesses:\n%s', blame)}\n\n{resolution_info}"
            )
        else:
            message = f"{operation_error}\n{failing_model}\n\n{resolution_info}"
        records.invalidate_recordset()
        exception = AccessError(message)
        if context:
            exception.context = context
        return exception

    def _get_failed_accesses(self, records: Any, operation: str) -> Self:
        letter = self._operation_letter(operation)
        model = records.browse().sudo().with_context(active_test=False)
        group_ids = set(self.env.user._get_group_ids())
        eval_context = self._eval_context()

        def domain_of(row: AccessInfo) -> Domain:
            if isinstance(row.domain, Domain):
                return row.domain
            return Domain(safe_eval(row.domain, eval_context))

        def admits_all(domain: Domain) -> bool:
            return len(records.with_env(model.env).filtered_domain(domain)) == len(
                records
            )

        rows = [
            row
            for row in self._get_all_access().get(model._name, ())
            if letter in row.operation
        ]
        permissions = [
            row
            for row in rows
            if row.kind == "permission" and row.group_id in group_ids
        ]
        failing = []
        if not admits_all(Domain.OR(domain_of(row) for row in permissions)):
            failing.extend(permissions)
        failing.extend(
            row
            for row in rows
            if row.kind == "guard"
            and (row.guard_scope == "everyone" or row.group_id in group_ids)
            and not admits_all(domain_of(row))
        )
        return self.sudo().browse(row.id for row in failing)
