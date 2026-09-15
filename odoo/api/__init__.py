from typing import Self

from odoo.orm._typing import DomainType
from odoo.orm.primitives import (
    MODULE_UNINSTALL_FLAG,
    SUPERUSER_ID,
    ContextType,
    IdType,
    NewId,
    ValuesType,
)
from odoo.orm.decorators import (
    autovacuum,
    constrains,
    depends,
    depends_context,
    deprecated,
    is_readonly,
    job,
    model,
    model_create_multi,
    onchange,
    ondelete,
    private,
    readonly,
)
from odoo.orm.runtime import Environment

__all__ = [
    "MODULE_UNINSTALL_FLAG",
    "SUPERUSER_ID",
    "ContextType",
    "DomainType",
    "Environment",
    "IdType",
    "NewId",
    "Self",
    "ValuesType",
    "autovacuum",
    "constrains",
    "depends",
    "depends_context",
    "deprecated",
    "is_readonly",
    "job",
    "model",
    "model_create_multi",
    "onchange",
    "ondelete",
    "private",
    "readonly",
]
