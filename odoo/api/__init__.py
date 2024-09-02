# ruff: noqa: F401
# Exports features of the ORM to developers.
# This is a `__init__.py` file to avoid merge conflicts on `odoo/api.py`.
from odoo.orm.identifiers import NewId
from odoo.orm.decorators import (
    autovacuum,
    constrains,
    depends,
    depends_context,
    model,
    model_create_multi,
    onchange,
    ondelete,
    readonly,
)
from odoo.orm.environments import Environment

from odoo.orm.types import ContextType, DomainType, IdType, Self, ValuesType
