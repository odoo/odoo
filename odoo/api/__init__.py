# ruff: noqa: F401
# Exports features of the ORM to developers.
# This is a `__init__.py` file to avoid merge conflicts on `odoo/api.py`.
from odoo._orm.identifiers import NewId
from odoo._orm.api import (
    Environment,
    autovacuum,
    call_kw,
    constrains,
    depends,
    depends_context,
    model,
    model_create_multi,
    onchange,
    ondelete,
    readonly,
    returns,
)

from odoo._orm.types import ContextType, DomainType, IdType, Self, ValuesType
