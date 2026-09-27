"""The implementation of the ORM.

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
# import first for core setup
import odoo.init  # noqa: F401
