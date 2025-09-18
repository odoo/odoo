# Exports features of the ORM to developers.
# This is a `__init__.py` file to avoid merge conflicts on `odoo/api.py`.
from odoo.orm._typing import DomainType
from odoo.orm.primitives import (
    SUPERUSER_ID,
    ContextType,
    IdType,
    NewId,
    Self,
    ValuesType,
)
from odoo.orm.decorators import (
    autovacuum,
    constrains,
    depends,
    depends_context,
    deprecated,
    model,
    model_create_multi,
    onchange,
    ondelete,
    private,
    readonly,
)
from odoo.orm.runtime import Environment
