import ast
import logging
import re
import typing
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping
from typing import Any, Self

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import AccessError, UserError, ValidationError
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
# a domain that can hold an 'access' condition: only those are parsed for the
# cycle check (an unrelated text is not evaluated, which a rule calling back
# into the decision would turn into a recursion)
ACCESS_OPERATOR_RE = re.compile(r"""['"]access['"]""")
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
    name: str = ""
    text: str = ""


def parse_access_domain(text: str | None) -> Domain | str:
    # a literal domain is parsed once; one that reads the user or the companies
    # stays text and is evaluated for each principal
    text = (text or "").strip()
    if not text:
        return Domain.TRUE
    try:
        return Domain(ast.literal_eval(text))
    except ValueError, SyntaxError, TypeError:
        return text


def _monotone_group_reads(tree: ast.AST) -> set[int]:
    # the two readings of the principal's groups that more groups can only
    # widen: membership in the ids of the user's groups, and an exemption that
    # drops the domain altogether for the members of a group
    allowed: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)):
            for index, item in enumerate(node.elts):
                if not (
                    isinstance(item, (ast.Tuple, ast.List))
                    and len(item.elts) == 3
                    and isinstance(item.elts[1], ast.Constant)
                    and item.elts[1].value == "in"
                ):
                    continue
                previous = node.elts[index - 1] if index else None
                if isinstance(previous, ast.Constant) and previous.value == "!":
                    continue
                value = item.elts[2]
                if (
                    isinstance(value, ast.Attribute)
                    and value.attr == "ids"
                    and isinstance(value.value, ast.Attribute)
                    and value.value.attr in ("all_group_ids", "group_ids")
                ):
                    allowed.add(id(value.value))
        elif (
            isinstance(node, ast.IfExp)
            and isinstance(node.test, ast.Call)
            and isinstance(node.test.func, ast.Attribute)
            and node.test.func.attr == "has_group"
            and _widens(node)
        ):
            allowed.add(id(node.test.func))
    return allowed


def _widens(node: ast.IfExp) -> bool:
    # [] if member else D: the members are exempt; ['|', A] if member else []
    # put before a domain: the members also reach A
    if isinstance(node.body, ast.List) and not node.body.elts:
        return True
    return (
        isinstance(node.orelse, ast.List)
        and not node.orelse.elts
        and isinstance(node.body, ast.List)
        and bool(node.body.elts)
        and isinstance(node.body.elts[0], ast.Constant)
        and node.body.elts[0].value == "|"
    )


def domain_group_tests(domain: str) -> list[str]:
    # a domain that tests the principal's groups can make a group take records
    # away; the row's group is where membership is stated
    try:
        tree = ast.parse(domain.strip(), mode="eval")
    except SyntaxError:
        return []
    allowed = _monotone_group_reads(tree)
    return sorted(
        {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and node.attr in GROUP_TESTS
            and id(node) not in allowed
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
                self.env._(
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
                    self.env._(
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
                    self.env._(
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

    def _access_cycle_message(self, cycle: list[tuple[str, str]]) -> str:
        return self.env._(
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
                if not ACCESS_OPERATOR_RE.search(row.text):
                    continue
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

    @api.model
    def _load_records(self, data_list: list[dict], update: bool = False) -> Self:
        # a module's rows reuse the external ids of the access lines and rules
        # they were converted from; base's 1.97 migration moves those ids onto
        # the rows before any module loads, so a database that still maps one
        # to an old record has not run it
        if old := (
            self.env["ir.model.data"]
            .sudo()
            .search([("model", "in", ("ir.model.access", "ir.rule"))], limit=1)
        ):
            raise UserError(
                self.env._(
                    "This database still holds access lines and record rules "
                    "(%(xmlid)s among them), which base's 1.97 migration converts "
                    "into ir.access rows. Upgrade base first (-u base), then the "
                    "other modules.",
                    xmlid=f"{old.module}.{old.name}",
                )
            )
        self._check_guard_scope_stated(data_list)
        return super()._load_records(data_list, update)

    def _check_guard_scope_stated(self, data_list: list[dict]) -> None:
        # a guard on a group defaults to binding every principal, which a file
        # naming a group almost never means (marin's CSV row did exactly this)
        everyone = self.env.ref("base.group_everyone", raise_if_not_found=False)
        for data in data_list:
            values = data["values"]
            if values.get("kind") != "guard" or "guard_scope" in values:
                continue
            group_id = values.get("group_id")
            if not group_id or (everyone and group_id == everyone.id):
                continue
            raise ValidationError(
                self.env._(
                    "%(file)s: the guard %(xmlid)s is on a group other than "
                    "Everyone but does not say whom it binds. State its "
                    "guard_scope: 'members' binds that group's members, "
                    "'everyone' binds every user (a CSV row that needs it goes "
                    "to security/ir_access.xml).",
                    file=self.env.context.get("install_filename")
                    or self.env.context.get("install_module")
                    or "",
                    xmlid=data.get("xml_id") or values.get("name"),
                )
            )

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
        # views bake the groups a model is readable by into their cached arch
        self.env.registry.clear_cache("stable", "templates")

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

    @api.model
    def _eval_context(self) -> dict[str, Any]:
        # modules extend it (website adds the current website); the user comes
        # with an empty context, so a domain reads the same in every context
        return {
            "user": self.env.user.with_context({}),
            "company_ids": self.env.companies.ids,
            "company_id": self.env.company.id,
            "time": time,
        }

    def _get_access_context(self) -> Iterator[Any]:
        # the context values the evaluation of a domain depends on
        company_ids = self.env.context.get("allowed_company_ids")
        yield tuple(company_ids) if isinstance(company_ids, list) else company_ids

    def _get_unloaded_module_scope(self) -> tuple[int, str | None] | None:
        return unloaded_module_scope(self.env)

    def _policy_signature(self) -> tuple:
        env = self.env
        return (
            env.uid,
            env.user._get_group_ids(),
            tuple(self._get_access_context()),
            unloaded_module_scope(env),
        )

    def _access_infos(self, accesses: Self) -> dict[str, tuple[AccessInfo, ...]]:
        result: defaultdict[str, list[AccessInfo]] = defaultdict(list)
        registry = self.env.registry
        for access in accesses:
            model_name = access.model_id.model
            if model_name not in registry:
                continue
            text = (access.domain or "").strip()
            result[model_name].append(
                AccessInfo(
                    access.id,
                    access.group_id.id,
                    access.kind,
                    access.guard_scope,
                    access.operation,
                    parse_access_domain(text),
                    access.name,
                    text,
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
        # a model with its own table under a table-inheritance root is bound by
        # the root's rows too, as the rows are read through the root's table
        for model_name in list(self.env.registry.models):
            for other in self._get_models_bound_by(model_name)[1:]:
                infos[model_name] = infos.get(model_name, ()) + infos.get(other, ())
        if cycle := self._access_cycle(infos):
            raise ValueError(self._access_cycle_message(cycle))
        _debug.perf.count("accesses_loaded", rows=len(accesses), models=len(infos))
        return frozendict(infos)

    def _get_models_bound_by(self, model_name: str) -> list[str]:
        # a model with its own table under a table-inheritance root is bound by
        # the root's rows too, as its records are read through the root's table
        registry = self.env.registry
        model_cls = registry.get(model_name)
        root = getattr(model_cls, "_table_inheritance_root", "")
        if not root or model_cls._table == root:
            return [model_name]
        return [model_name] + [
            name
            for name in registry.model_names_by_inheritance_root.get(root, ())
            if registry[name]._table == root
        ]

    def _bound_access_rows(
        self, model_name: str, operation: str
    ) -> tuple[list[Domain], list[Domain]]:
        # the domains of the permissions the principal's groups hold and of the
        # guards that bind it, for one model and operation
        letter = self._operation_letter(operation)
        group_ids = set(self.env.user._get_group_ids())
        permissions: list[Domain] = []
        guards: list[Domain] = []
        eval_context = None
        for row in self._get_all_access().get(model_name, ()):
            if letter not in row.operation:
                continue
            binds = row.kind == "guard" and row.guard_scope == "everyone"
            if not binds and row.group_id not in group_ids:
                continue
            domain = row.domain
            if not isinstance(domain, Domain):
                if eval_context is None:
                    eval_context = self._eval_context()
                domain = Domain(safe_eval(domain, eval_context))
            (permissions if row.kind == "permission" else guards).append(domain)
        return permissions, guards

    def _get_groups_with_access(self, model_name: str, operation: str) -> Any:
        # the groups whose members may perform the operation on some records of
        # the model: a permission's group or a group implying it, for which the
        # 'access' conditions of the row, the guards binding it, the model's own
        # guard and every delegated parent can all hold
        return (
            self.env["res.groups"]
            .sudo()
            .browse(sorted(self._group_ids_with_access(model_name, operation)))
        )

    @tools.ormcache("model_name", "operation", cache="stable")
    def _group_ids_with_access(self, model_name: str, operation: str) -> frozenset[int]:
        letter = self._operation_letter(operation)
        implying = self._group_ids_implying()
        every_group = frozenset(implying)
        model = self.env[model_name].sudo()
        rows = [
            row
            for row in self._get_all_access().get(model_name, ())
            if letter in row.operation
        ]
        groups: set[int] = set()
        for row in rows:
            if row.kind == "permission":
                groups |= implying.get(row.group_id, frozenset()) & (
                    self._group_ids_satisfying(model, self._row_access_domain(row))
                )
        for row in rows:
            if row.kind == "guard":
                allowed = self._group_ids_satisfying(
                    model, self._row_access_domain(row)
                )
                if row.guard_scope == "members":
                    allowed |= every_group - implying.get(row.group_id, frozenset())
                groups &= allowed
        groups &= self._group_ids_satisfying(model, model._access_guard(operation))
        if model._inherits_rules:
            for parent_model_name, field_name in model._inherits.items():
                if operation == "create" and not model._fields[field_name].store:
                    continue
                groups &= self._group_ids_with_access(parent_model_name, operation)
        return frozenset(groups)

    @tools.ormcache(cache="stable")
    def _group_ids_implying(self) -> frozendict:
        groups = self.env["res.groups"].sudo().with_context(active_test=False)
        return frozendict(
            {
                group.id: frozenset(group.all_implied_by_ids.ids) | {group.id}
                for group in groups.search([])
            }
        )

    def _row_access_domain(self, row: AccessInfo) -> Domain:
        # what a group needs of a row is only its 'access' conditions, the rest
        # can hold for some records whatever the group; a text domain is read
        # only when it can hold such a condition
        if isinstance(row.domain, Domain):
            return row.domain
        if not ACCESS_OPERATOR_RE.search(row.text):
            return Domain.TRUE
        try:
            return Domain(safe_eval(row.domain, self._eval_context()))
        except Exception:
            _logger.warning("Access %s: its domain does not evaluate", row.id)
            return Domain.TRUE

    def _group_ids_satisfying(
        self, model: models.BaseModel, domain: Domain
    ) -> frozenset[int]:
        every_group = frozenset(self._group_ids_implying())

        def combine(domain: Domain) -> frozenset[int]:
            if domain.is_true():
                return every_group
            if domain.is_false():
                return frozenset()
            if isinstance(domain, DomainCondition):
                comodel_name = (
                    model._name
                    if domain.field_expr == "id"
                    else model._fields[domain.field_expr].comodel_name
                )
                return self._group_ids_with_access(comodel_name, domain.value)
            operator = getattr(domain, "OPERATOR", None)
            if operator == "|":
                return frozenset().union(*map(combine, domain.children))
            if operator == "&":
                result = every_group
                for child in domain.children:
                    result &= combine(child)
                return result
            if operator == "!":
                return every_group - combine(domain.child)
            return every_group

        return combine(
            domain.map_conditions(
                lambda condition: (
                    condition if condition.operator == "access" else Domain.TRUE
                )
            )
        )

    def _group_names_with_access(self, model_name: str, operation: str) -> list[str]:
        # a group implying another group of the list adds nothing to read
        groups = self._get_groups_with_access(model_name, operation)
        shown = groups.filtered(
            lambda group: not ((group.all_implied_ids - group) & groups)
        )
        names = sorted(
            ((group.privilege_id.name or None, group.name) for group in shown),
            key=lambda pair: (pair[0] is None, pair[0] or "", pair[1]),
        )
        return [
            f"{privilege}/{group}" if privilege else group for privilege, group in names
        ]

    def _make_model_access_error(self, model_name: str, operation: str) -> AccessError:
        _logger.info(
            "Access Denied by ACLs for operation: %s, uid: %s, model: %s",
            operation,
            self.env.uid,
            model_name,
        )
        operation_error = str(ACCESS_ERROR_HEADER[operation]) % {
            "document_kind": self.env["ir.model"]._get(model_name).name or model_name,
            "document_model": model_name,
        }
        groups = "\n".join(
            f"\t- {name}"
            for name in self._group_names_with_access(model_name, operation)
        )
        if groups:
            group_info = str(ACCESS_ERROR_GROUPS) % {"groups_list": groups}
        else:
            group_info = str(ACCESS_ERROR_NOGROUP)
        return AccessError(
            "\n\n".join([operation_error, group_info, str(ACCESS_ERROR_RESOLUTION)])
        )

    def _make_record_access_error(self, records: Any, operation: str) -> AccessError:
        _logger.info(
            "Access Denied by record rules for operation: %s on record ids: %r, uid: %s, model: %s",
            operation,
            records.ids[:6],
            self.env.uid,
            records._name,
        )
        self = self.with_context(self.env.user.context_get())
        model_name = records._name
        description = self.env["ir.model"]._get(model_name).name or model_name
        operation_names = {
            "read": self.env._("read"),
            "write": self.env._("write"),
            "create": self.env._("create"),
            "unlink": self.env._("unlink"),
        }
        operation_error = self.env._(
            "Uh-oh! Looks like you have stumbled upon some top-secret records.\n\n"
            "Sorry, %(user)s doesn't have '%(operation)s' access to:",
            user=f"{self.env.user.name} (id={self.env.uid})",
            operation=operation_names.get(operation, operation),
        )
        failing_model = self.env._(
            "- %(description)s (%(model)s)", description=description, model=model_name
        )
        resolution_info = self.env._(
            "If you really, really need access, perhaps you can win over your "
            "friendly administrator with a batch of freshly baked cookies."
        )
        debug = (
            self.env.user.has_group("base.group_no_one")
            and self.env.user._is_internal()
        )
        display_records = records[:6].sudo()
        failing = self._get_failed_accesses(records, operation)
        company_related = any("company_id" in row.text for row in failing)
        context = None
        if company_related:
            resolution_info, context = self._get_company_resolution_info(
                display_records, resolution_info
            )

        def describe(record: Any) -> str:
            if (
                company_related
                and "company_id" in record
                and record.company_id in self.env.user.company_ids
            ):
                return (
                    f"{description}, {record.display_name} ({model_name}: "
                    f"{record.id}, company={record.company_id.display_name})"
                )
            return f"{description}, {record.display_name} ({model_name}: {record.id})"

        if debug:
            failing_records = "\n".join(
                f"- {describe(record)}" for record in display_records
            )
            blame = "\n\n".join(self._blame(failing))
            message = (
                f"{operation_error}\n{failing_records}\n\n{blame}\n\n{resolution_info}"
            )
        else:
            message = f"{operation_error}\n{failing_model}\n\n{resolution_info}"
        records.invalidate_recordset()
        exception = AccessError(message)
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
            resolution_info += self.env._(
                "\n\nNote: this might be a multi-company issue. Switching company may help - in Odoo, not in real life!"
            )
        elif suggested_companies and suggested_companies in self.env.user.company_ids:
            context = {
                "suggested_company": {
                    "id": suggested_companies.id,
                    "display_name": suggested_companies.display_name,
                }
            }
            resolution_info += self.env._(
                "\n\nThis seems to be a multi-company issue, you might be able to access the record by switching to the company: %s.",
                suggested_companies.display_name,
            )
        elif suggested_companies:
            resolution_info += self.env._(
                "\n\nThis seems to be a multi-company issue, but you do not have access to the proper company to access the record anyhow."
            )
        return resolution_info, context

    def _blame(self, failing: list[AccessInfo]) -> list[str]:
        accesses = sorted(
            {(row.id, row.name): row for row in failing}.values(),
            key=lambda row: (row.id == 0, row.id, row.name),
        )
        return [
            self.env._(
                "Blame the following accesses:\n%s",
                "\n".join(f"- {row.name}" for row in accesses),
            )
        ]

    def _get_failed_accesses(self, records: Any, operation: str) -> list[AccessInfo]:
        # the rows, the model's own guard and the delegated parents' rows that
        # refuse some of the records: permissions fail together (they add up),
        # each guard fails on its own
        letter = self._operation_letter(operation)
        user_model = records.browse()
        model = user_model.sudo().with_context(active_test=False)
        group_ids = set(self.env.user._get_group_ids())
        eval_context = self._eval_context()

        def domain_of(row: AccessInfo) -> Domain:
            if isinstance(row.domain, Domain):
                return row.domain
            return Domain(safe_eval(row.domain, eval_context))

        # counted in SQL: evaluating in Python would fill the cache of the
        # records' prefetch batch with values the principal may not read
        ids = list(dict.fromkeys(id_ for id_ in records._ids if id_))

        def admitted(target: models.BaseModel, domain: Domain, among: list) -> set:
            return set(target.search(domain & Domain("id", "in", among))._ids)

        def admits_all(domain: Domain) -> bool:
            return len(admitted(model, domain, ids)) == len(ids)

        def holds(row: AccessInfo) -> bool:
            return row.group_id in group_ids

        rows = [
            row
            for row in self._get_all_access().get(model._name, ())
            if letter in row.operation
        ]
        permissions = [row for row in rows if row.kind == "permission" and holds(row)]
        failing: list[AccessInfo] = []
        if not admits_all(Domain.OR(domain_of(row) for row in permissions)):
            failing.extend(permissions)
        failing.extend(
            row
            for row in rows
            if row.kind == "guard"
            and (row.guard_scope == "everyone" or holds(row))
            and not admits_all(domain_of(row))
        )
        own = user_model._access_guard(operation)
        if not own.is_true() and not admits_all(own):
            failing.append(
                AccessInfo(
                    0,
                    0,
                    "guard",
                    "everyone",
                    letter,
                    own,
                    self.env._("the condition of %(model)s itself", model=model._name),
                    str(own),
                )
            )
        if model._inherits_rules:
            policy = self.env.registry.access_policy
            for parent_model_name, field_name in model._inherits.items():
                if operation == "create" and not model._fields[field_name].store:
                    continue
                parent_ids = list(dict.fromkeys(model.browse(ids)[field_name]._ids))
                parent = (
                    self.env[parent_model_name].sudo().with_context(active_test=False)
                )
                parent_domain = policy.security_domain(
                    self.env, parent_model_name, operation
                )
                allowed = admitted(parent, parent_domain, parent_ids)
                refused = [id_ for id_ in parent_ids if id_ not in allowed]
                if not refused:
                    continue
                through = self.env._(
                    "through %(field)s, %(model)s",
                    field=field_name,
                    model=parent_model_name,
                )
                parent_failing = self._get_failed_accesses(
                    self.env[parent_model_name].browse(refused), operation
                ) or [
                    AccessInfo(
                        0,
                        0,
                        "permission",
                        "everyone",
                        letter,
                        Domain.FALSE,
                        self.env._("no permission"),
                        "",
                    )
                ]
                failing.extend(
                    row._replace(name=f"{row.name} ({through})")
                    for row in parent_failing
                )
        return failing
