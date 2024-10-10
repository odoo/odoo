# ruff: noqa: F401
""" The implementation of the ORM.

A `Registry` object is instantiated per database, and exposes all the available
models for its database. The available models are determined by the modules
that must be loaded for the given database.
The `decorators` defines various method decorators.
The 'environments` defines `Transaction`, collecting database
transaction-specific data, and `Environment`, which contains specific
context-dependent data inside a transaction.

The `fields` file defines the base class of fields for models.
After loading it, you may load scalar fields.
Finally, `models` provides the base classes for defining models.
You may now define relational fields.

We export the needed features in various packages and developers should not
import directly from here.
"""

# We import in an order that describes the dependencies between modules.
# We need to import at least `model` and the rest is optional here.

from . import registry
from . import environments

# setup Field definition
# you may now import scalar field types (optional)
from . import fields

# setup models
from . import models

# you may now import relational field types (optional)

# TODO future: import domains manipulation
# from odoo.osv import expression is not importing directly from orm
