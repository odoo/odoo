"""
ORM Fields package.

This package provides all field types for Odoo models:

Scalar Fields:
    - Boolean, Json, Id (misc.py)
    - Integer, Float, Monetary (numeric.py)
    - Char, Text, Html (textual.py)
    - Selection (selection.py)
    - Date, Datetime (temporal.py)

Binary Fields:
    - Binary, Image (binary.py)

Relational Fields:
    - Many2one, One2many, Many2many (relational.py)
    - Reference, Many2oneReference (reference.py)

Special Fields:
    - Properties, PropertiesDefinition (properties.py)

Usage:
    from odoo.orm.fields import Field, Many2one, Char, Integer
    # or via public API
    from odoo.fields import Field, Many2one, Char, Integer
"""

# Base field class and utilities (no model dependencies)
from .base import (
    COMPANY_DEPENDENT_FIELDS,
    IR_MODELS,
    Field,
    determine,
    resolve_mro,
)

# Binary field types (no model dependencies)
from .binary import Binary, Image

# Scalar field types (no model dependencies)
from .misc import Boolean, Id, Json
from .numeric import Float, Integer, Monetary

# Properties field types
from .properties import (
    Properties,
    PropertiesDefinition,
    check_property_field_value_name,
)

# Reference field types
from .reference import Many2oneReference, Reference

# Relational field types
from .relational import Many2many, Many2one, One2many
from .selection import Selection
from .temporal import Date, Datetime
from .textual import Char, Html, Text

__all__ = [
    "COMPANY_DEPENDENT_FIELDS",
    "IR_MODELS",
    # Binary
    "Binary",
    # Scalar - misc
    "Boolean",
    # Scalar - textual
    "Char",
    # Scalar - temporal
    "Date",
    "Datetime",
    # Base
    "Field",
    "Float",
    "Html",
    "Id",
    "Image",
    # Scalar - numeric
    "Integer",
    "Json",
    "Many2many",
    # Relational
    "Many2one",
    "Many2oneReference",
    "Monetary",
    "One2many",
    # Properties
    "Properties",
    "PropertiesDefinition",
    # Reference
    "Reference",
    # Scalar - selection
    "Selection",
    "Text",
    "check_property_field_value_name",
    "determine",
    "resolve_mro",
]
