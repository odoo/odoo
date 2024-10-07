# ruff: noqa: F401
# Exports features of the ORM to developers.
# This is a `__init__.py` file to avoid merge conflicts on `odoo/api.py`.
from odoo.orm.api import (
    Environment,
    NewId,
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
