# Exports features of the ORM to developers.
# This is a `__init__.py` file to avoid merge conflicts on `odoo/fields.py`.

from odoo.orm.primitives import NO_ACCESS, Command
from odoo.orm.domain import (
    CONDITION_OPERATORS,
    Domain,
    DomainCondition,
    OptimizationLevel,
    operator_optimization,
)
from odoo.orm.fields import (
    # Base
    Field,
    # Scalar types
    Id,
    Boolean,
    Json,
    Integer,
    Float,
    Monetary,
    Char,
    Text,
    Html,
    Selection,
    Date,
    Datetime,
    Binary,
    Image,
    # Relational types
    Many2one,
    One2many,
    Many2many,
    Reference,
    Many2oneReference,
    # Special types
    Properties,
    PropertiesDefinition,
)
from odoo.orm.parsing import parse_field_expr
