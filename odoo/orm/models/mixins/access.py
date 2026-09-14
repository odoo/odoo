import functools
import logging
import typing
from collections import defaultdict
from operator import itemgetter
from typing import Self

from odoo.exceptions import AccessError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import unquote
from odoo.tools.translate import LazyTranslate, _

from ... import decorators as api
from ...domain import Domain
from ...fields.base import call_hook
from ...helpers import to_record_ids
from ...primitives import NO_ACCESS
from ._model_stubs import _ModelStubs

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterator

    from ...fields import Field

_lt = LazyTranslate("base")

_logger = logging.getLogger("odoo.models")
_debug = DebugLog(__name__)


class AccessMixin(_ModelStubs):
    __slots__ = ()

    def _has_field_access(
        self, field: Field, operation: typing.Literal["read", "write"]
    ) -> bool:
        if not (field.groups or field.write_groups) or self.env.su:
            return True
        if field.groups:
            if field.groups == NO_ACCESS:
                return False
            if not self.env.user.has_groups(field.groups):
                return False
        if operation == "write" and field.write_groups:
            return self._has_write_groups(field)
        return True

    def _has_write_groups(self, field: Field) -> bool:
        write_groups = field.write_groups
        if write_groups == NO_ACCESS:
            return False
        if callable(write_groups):
            return bool(call_hook(write_groups, self))
        return self.env.user.has_groups(write_groups)

    @api.model
    def _check_fields_write_access(self, field_names: typing.Iterable[str]) -> None:
        for field_name in field_names:
            field = self._fields.get(field_name)
            if field is None:
                raise ValueError(f"Invalid field {field_name!r} in {self._name!r}")
            self._check_field_access(field, "write")

    def _check_field_access(
        self, field: Field, operation: typing.Literal["read", "write"]
    ) -> None:
        if self._has_field_access(field, operation):
            return

        _logger.info(
            "Access Denied by ACLs for operation: %s, uid: %s, model: %s, field: %s",
            operation,
            self.env.uid,
            self._name,
            field.name,
        )
        _debug.logic(
            "access.field_denied",
            model=self._name,
            field=field.name,
            operation=operation,
            uid=self.env.uid,
            groups=field.groups,
            write_groups=bool(field.write_groups),
        )

        description = self.env.registry.metaschema.model_description(
            self.env, self._name
        )

        error_msg = _(
            'You do not have enough rights to access the field "%(field)s"'
            " on %(document_kind)s (%(document_model)s). "
            "Please contact your system administrator."
            "\n\nOperation: %(operation)s",
            field=field.name,
            document_kind=description,
            document_model=self._name,
            operation=operation,
        )

        if self.env.user._has_group("base.group_no_one"):
            error_msg += _(
                "\nUser: %(user)s\nGroups: %(allowed_groups_msg)s",
                user=self.env.uid,
                allowed_groups_msg=self._get_field_access_message(field, operation),
            )

        raise AccessError(error_msg)

    @api.model
    def _get_field_access_message(
        self, field: Field, operation: typing.Literal["read", "write"]
    ) -> str:
        if field.groups == NO_ACCESS:
            return _("always forbidden")

        messages = []
        if field.groups:
            messages.append(self._get_group_spec_message(field.groups))
        if operation == "write" and field.write_groups:
            if field.write_groups == NO_ACCESS:
                messages.append(_("write always forbidden"))
            elif callable(field.write_groups):
                messages.append(_("write gated by a field predicate"))
            else:
                messages.append(
                    _(
                        "write %(spec)s",
                        spec=self._get_group_spec_message(field.write_groups),
                    )
                )
        if not messages:
            return _("custom field access rules")
        return ", ".join(messages)

    @api.model
    def _get_group_spec_message(self, group_spec: str) -> str:
        groups_list = []
        missing_xmlids = []
        for xmlid in group_spec.split(","):
            group = self.env.ref(xmlid.strip(), raise_if_not_found=False)
            if group is not None and group._name == "res.groups":
                groups_list.append(group)
            else:
                missing_xmlids.append(xmlid.strip())
        groups = self.env["res.groups"].union(*groups_list).sorted("id")
        if _debug.logic.enabled and missing_xmlids:
            _debug.logic(
                "access.group_spec_unresolved",
                model=self._name,
                spec=group_spec,
                missing=missing_xmlids,
            )
        return _(
            "allowed for groups %s",
            ", ".join([repr(g.display_name) for g in groups] + missing_xmlids),
        )

    @api.model
    def check_access(self, operation: str) -> None:
        if not self.env.su and (result := self._check_access(operation)):
            raise result[1]()  # noqa: RSE102  result[1] builds the exception, it is not the class

    def has_access(self, operation: str) -> bool:
        return self.env.su or not self._check_access(operation)

    def _filtered_access(self, operation: str) -> Self:
        if self and not self.env.su and (result := self._check_access(operation)):
            return self - result[0]
        return self

    def _get_display_name_visible_ids(self) -> set[int]:
        return set()

    def _filtered_display_name_access(self) -> Self:
        readable = self._filtered_access("read")
        hidden = self - readable
        if not hidden:
            return readable
        visible_ids = hidden._get_display_name_visible_ids() & set(hidden._ids)
        allowed_ids = set(readable._ids) | visible_ids
        _debug.logic(
            "access.display_name_filtered",
            model=self._name,
            uid=self.env.uid,
            records=len(self),
            hidden=len(hidden),
            visible_by_name=len(visible_ids),
        )
        return self.browse(id_ for id_ in self._ids if id_ in allowed_ids)

    def _check_access(self, operation: str) -> tuple[Self, Callable] | None:
        policy = self.env.registry.access_policy
        if not policy.model_allowed(self.env, self._name, operation):
            _debug.logic(
                "access.denied_by_acl",
                model=self._name,
                operation=operation,
                uid=self.env.uid,
                records=len(self),
            )
            return self, functools.partial(
                policy.model_denied_error, self.env, self._name, operation
            )

        # keep the prefetch ids: the rules' Python evaluation on one record
        # of a batch would otherwise fetch that record's row alone
        real_ids = tuple(id_ for id_ in self._ids if id_)
        real_self = (
            self
            if len(real_ids) == len(self._ids)
            else self._spawn(self.env, real_ids, self._prefetch_ids)
        )
        if real_self:
            domain = policy.record_domain(self.env, self._name, operation)
            if domain and (
                forbidden := real_self
                - real_self.sudo()
                .with_context(active_test=False)
                .filtered_domain(domain)
            ):
                _debug.logic(
                    "access.denied_by_rule",
                    model=self._name,
                    operation=operation,
                    uid=self.env.uid,
                    records=len(real_self),
                    forbidden=len(forbidden),
                )
                return forbidden, functools.partial(
                    policy.record_denied_error, self.env, operation, forbidden
                )

        return None

    def _check_company_domain(self, companies) -> Domain:
        if not companies:
            return Domain("company_id", "=", False)
        if isinstance(companies, unquote):
            return Domain("company_id", "in", unquote(f"{companies} + [False]"))
        return Domain("company_id", "in", to_record_ids(companies) + [False])

    def _get_company_check_candidates(
        self, regular_fields: list[str], property_fields: list[str]
    ) -> dict[tuple, list[tuple]]:
        groups: dict[tuple, list[tuple]] = defaultdict(list)
        property_company = self.env.company
        width = len(regular_fields) + len(property_fields)
        scopes = [(regular_fields, None), (property_fields, property_company)]

        for record_index, record_su in enumerate(self.sudo()):
            record = record_su.sudo(self.env.su)
            offset = 0
            for names, fixed_companies in scopes:
                if fixed_companies is None and names:
                    companies = (
                        record
                        if self._name == "res.company"
                        else record["company_id"]
                        if "company_id" in self
                        else record["company_ids"]
                    )
                else:
                    companies = fixed_companies
                for position, name in enumerate(names):
                    corecords = record_su[name]
                    if corecords:
                        groups[(name, tuple(companies.ids))].append(
                            (
                                record_index * width + offset + position,
                                record,
                                corecords,
                                companies,
                            )
                        )
                offset += len(names)
        _debug.pipeline(
            "access.company_candidates",
            model=self._name,
            records=len(self),
            regular_fields=len(regular_fields),
            property_fields=len(property_fields),
            groups=len(groups),
        )
        return groups

    def _get_company_violations(
        self, groups: dict[tuple, list[tuple]]
    ) -> Iterator[tuple[int, Self, str, Self]]:
        for (name, _companies_ids), entries in groups.items():
            companies = entries[0][3]
            comodel = entries[0][2].browse()
            all_corecords = comodel.union(*(entry[2] for entry in entries))
            domain = all_corecords._check_company_domain(companies)
            if not domain:
                continue
            allowed = set(
                all_corecords.with_context(active_test=False)
                .filtered_domain(domain)
                ._ids
            )
            for rank, record, corecords, _companies in entries:
                if not allowed.issuperset(corecords._ids):
                    yield rank, record, name, corecords

    def _check_company(self, fnames: Collection[str] | None = None) -> None:
        if fnames is None or "company_id" in fnames or "company_ids" in fnames:
            fnames = self._fields

        regular_fields = []
        property_fields = []
        for name in fnames:
            field = self._fields[name]
            if field.relational and field.check_company:
                if not field.company_dependent:
                    regular_fields.append(name)
                else:
                    property_fields.append(name)

        if not (regular_fields or property_fields):
            return

        if regular_fields and not (
            self._name == "res.company" or "company_id" in self or "company_ids" in self
        ):
            _logger.warning(
                "Skipping a company check for model %s. Its fields %s "
                "are set as company-dependent, but the model doesn't "
                "have a `company_id` or `company_ids` field!",
                self._name,
                regular_fields,
            )
            _debug.logic(
                "access.company_check_skipped",
                model=self._name,
                fields=regular_fields,
                reason="no_company_field",
            )
            return

        candidates = self._get_company_check_candidates(regular_fields, property_fields)
        inconsistencies = [
            (record, name, corecords)
            for _rank, record, name, corecords in sorted(
                self._get_company_violations(candidates), key=itemgetter(0)
            )
        ]

        if inconsistencies:
            _debug.logic(
                "access.company_inconsistent",
                model=self._name,
                records=len(self),
                violations=len(inconsistencies),
                fields=sorted({name for _record, name, _co in inconsistencies}),
            )
            lines = [_("Uh-oh! You've got some company inconsistencies here:")]
            company_msg = _lt(
                "- Record is company \u201c%(company)s\u201d while \u201c%(field)s\u201d (%(fname)s: %(values)s) belongs to another company."
            )
            record_msg = _lt(
                "- \u201c%(record)s\u201d belongs to company \u201c%(company)s\u201d while \u201c%(field)s\u201d (%(fname)s: %(values)s) belongs to another company."
            )
            root_company_msg = _lt(
                "- Only a root company can be set on \u201c%(record)s\u201d. Currently set to \u201c%(company)s\u201d"
            )
            for record, name, corecords in inconsistencies[:5]:
                if record._name == "res.company":
                    msg, companies = company_msg, record
                elif record == corecords and name == "company_id":
                    msg, companies = root_company_msg, record["company_id"]
                else:
                    msg = record_msg
                    companies = (
                        record["company_id"]
                        if "company_id" in record
                        else record["company_ids"]
                    )
                field_string = self.env.registry.metaschema.field_strings(
                    self.env, self._name
                ).get(name, self._fields[name].string)
                lines.append(
                    str(msg)
                    % {
                        "record": record.display_name,
                        "company": ", ".join(
                            company.display_name or "" for company in companies
                        ),
                        "field": field_string,
                        "fname": name,
                        "values": ", ".join(
                            repr(rec.display_name) for rec in corecords
                        ),
                    }
                )
            lines.append(_("To avoid a mess, no company crossover is allowed!"))
            raise UserError("\n".join(lines))
