import typing
from operator import itemgetter

from odoo.libs.debug_log import DebugLog

from ._recordset import is_recordset
from .domain import Domain

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

    from ._typing import ModelLike
    from .fields.base import Field
    from .models.base import BaseModel

_debug = DebugLog(__name__)


def get_fields_by_name(model: ModelLike, fnames: Iterable[str]) -> list[Field]:
    fields = []
    _fields = model._fields
    for fname in fnames:
        try:
            fields.append(_fields[fname])
        except KeyError:
            raise ValueError(
                f"Invalid field {fname!r} on model {model._name!r}"
            ) from None
    return fields


ORM_CLASS_MEMOS: tuple[str, ...] = (
    "_check_coupled_fields__",
    "_constrained_field_names__",
    "_constrained_projection_names__",
    "_constraint_methods__",
    "_onchange_methods__",
    "_ondelete_methods__",
    "_precompute_readonly_names__",
    "_properties_field_names__",
    "_stored_computed_fields__",
)


def get_or_create_class_memo[T](
    cls: type, key: str, factory: typing.Callable[[], T]
) -> T:
    value = cls.__dict__.get(key)
    if value is None:
        value = factory()
        setattr(cls, key, value)
    return value


def get_tuple_itemgetter(items: list | tuple) -> typing.Callable[[typing.Any], tuple]:
    if len(items) == 0:
        return lambda a: ()
    if len(items) == 1:
        return lambda gettable: (gettable[items[0]],)
    return itemgetter(*items)


def to_record_ids(arg) -> list[int]:
    if is_recordset(arg):
        return arg.ids
    elif isinstance(arg, bool):
        return []
    elif isinstance(arg, int):
        return [arg] if arg else []
    else:
        return [id_ for id_ in arg if id_]


def _get_ancestor_company_ids(self: BaseModel, company_ids: list[int]) -> list[int]:
    companies = self.env["res.company"].sudo().browse(company_ids)
    ancestor_ids = list(companies._get_ancestor_ids(include_self=True))
    _debug.logic(
        "helpers.company_ancestors",
        model=self._name,
        companies=len(company_ids),
        ancestors=len(ancestor_ids),
    )
    return ancestor_ids


def check_company_domain_parent_of(
    self: BaseModel,
    companies: BaseModel | list[int] | int | str,
) -> Domain:
    if isinstance(companies, str):
        _debug.logic(
            "helpers.check_company_domain",
            model=self._name,
            field="company_id",
            shape="unquoted_expression",
        )
        return Domain.OR(
            [
                Domain("company_id", "=", False),
                Domain("company_id", "parent_of", companies),
            ]
        )

    companies = to_record_ids(companies)
    if not companies:
        _debug.logic(
            "helpers.check_company_domain",
            model=self._name,
            field="company_id",
            shape="no_company",
        )
        return Domain("company_id", "=", False)

    return Domain(
        "company_id", "in", _get_ancestor_company_ids(self, companies) + [False]
    )


def check_companies_domain_parent_of(
    self: BaseModel,
    companies: BaseModel | list[int] | int | str,
) -> Domain:
    if isinstance(companies, str):
        return Domain("company_ids", "parent_of", companies)

    companies = to_record_ids(companies)
    if not companies:
        return Domain.TRUE

    return Domain("company_ids", "in", _get_ancestor_company_ids(self, companies))
