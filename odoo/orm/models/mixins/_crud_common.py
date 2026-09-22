import logging
import typing

from ...primitives import LOG_ACCESS_COLUMNS, SUPERUSER_ID

_BAD_NAMES = frozenset({"id", "parent_path"})
_BAD_NAMES_LOG = _BAD_NAMES | frozenset(LOG_ACCESS_COLUMNS)


def get_forbidden_field_names(model: typing.Any) -> frozenset:
    if model._log_access and not (
        model.env.uid == SUPERUSER_ID and not model.pool.ready
    ):
        return _BAD_NAMES_LOG
    return _BAD_NAMES


_unlink = logging.getLogger("odoo.models.unlink")
_orm_crud = logging.getLogger("odoo.orm.crud")
