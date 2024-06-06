# ruff: noqa: F401
# Exports features of the ORM to developers.
# This is a `__init__.py` file to avoid merge conflicts on `odoo/fields.py`.

from odoo.orm.fields import Field

from odoo.orm.fields_misc import Id, Json, Boolean
from odoo.orm.fields_numeric import Integer, Float, Monetary
from odoo.orm.fields_textual import Char, Text, Html
from odoo.orm.fields_selection import Selection
from odoo.orm.fields_temporal import Date, Datetime

from odoo.orm.fields_relational import Many2one, Many2many, One2many
from odoo.orm.fields_reference import Many2oneReference, Reference

from odoo.orm.fields_properties import Properties, PropertiesDefinition
from odoo.orm.fields_binary import Binary, Image

from odoo.orm.commands import Command
from odoo.orm.domains import Domain
from odoo.orm.models import NO_ACCESS
from odoo.orm.utils import parse_field_expr
