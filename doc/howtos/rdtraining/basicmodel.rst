.. _howto/rdtraining/basicmodel:

=======================
Models And Basic Fields
=======================

At the end of the :ref:`previous chapter <howto/rdtraining/newapp>`, we were able to create an Odoo
module. However, at this point it is still an empty shell which doesn't allow us to store any data.
In our real estate module, we want to store the information related to the properties
(name, description, price, living area...) in a database. The Odoo framework provides tools to
facilitate the interaction with the database.

Before moving forward on the excercise, make sure the ``estate`` module is installed, *i.e.* it
must appear as 'Installed' in the Apps list.

Object-Relational Mapping
=========================

**Reference**: the documentation related to this topic can be found in the
:ref:`reference/orm/model` API.

**Objectives**: at the end of this section, the table ``estate_property`` is created:

.. code-block:: console

    $ psql-d rd-demo
    rd-demo=# SELECT COUNT(*) FROM estate_property;
    count 
    -------
        0
    (1 row)

A key component of Odoo is the :abbr:`ORM (Object-Relational Mapping)` layer.
This layer avoids having to write most :abbr:`SQL (Structured Query Language)`
by hand and provides extensibility and security services\ [#rawsql]_.

Business objects are declared as Python classes extending
:class:`~odoo.models.Model` which integrates them into the automated
persistence system.

Models can be configured by setting a number of attributes at their
definition. The most important attribute is
:attr:`~odoo.models.Model._name` which is required and defines the name for
the model in the Odoo system. Here is a minimally complete definition of a
model::

    from odoo import models
    class TestModel(models.Model):
        _name = "test.model"

Such a definition is enough for the ORM to generate a database table named ``test_model``. The
``.`` in the model ``_name`` is automatically converted into a ``_`` by the ORM. By convention, all
models are located in a ``models`` directory. Moreover, each model is defined in its own Python
file.

Take a look at how the ``crm_recurring_plan`` table is defined, and how the corresponding Python
file is imported:

1. The model is defined in the file ``crm/models/crm_recurring_plan.py``
   (see `here <https://github.com/odoo/odoo/blob/e80911aaead031e7523173789e946ac1fd27c7dc/addons/crm/models/crm_recurring_plan.py#L1-L9>`__)
2. The file ``crm_recurring_plan.py`` is imported in ``crm/models/__init__.py``
   (see `here <https://github.com/odoo/odoo/blob/e80911aaead031e7523173789e946ac1fd27c7dc/addons/crm/models/__init__.py#L15>`__)
3. The folder ``models`` is imported in ``crm/__init__.py``
   (see `here <https://github.com/odoo/odoo/blob/e80911aaead031e7523173789e946ac1fd27c7dc/addons/crm/__init__.py#L5>`__)

.. exercise:: Define the real estate properties model

    Based on example given in the CRM module, create the appropriate files and folder for the
    ``estate_property`` table.

    When the files are created, use the minimally complete definition to add the
    ``estate.property`` model.

Any modification of the Python files requires a restart of the Odoo server. While we are restarting
the server, we will add the two parameters ``-d`` and ``-u``:

.. code-block:: console

    $ ./odoo-bin --addons-path=../custom,../enterprise/,addons -d rd-demo -u estate

``-u estate`` means that we want to upgrade the ``estate`` module, *i.e.* the ORM will
apply on database schema changes. In this case, it creates a new table. ``-d rd-demo`` means
that the upgrade should be performed on the ``rd-demo`` database. ``-u`` should always be used in
combination with ``-d``.

During the startup, you should see the following warnings:

.. code-block:: console

    ...
    WARNING rd-demo odoo.models: The model estate.property has no _description
    ...
    WARNING rd-demo odoo.modules.loading: The model estate.property has no access rules, consider adding one...
    ...

If this is the case, then you should be good! To be sure, double check with ``psql`` as suggested in
the **Objectives**.

.. exercise:: Add a description

    Add a ``_description`` to your model to get rid of one of the warnings.

Model fields
============

**Reference**: the documentation related to this topic can be found in the
:ref:`reference/orm/fields` API.

**Objectives**: at the end of this section, several basic fields are added to the table
``estate_property``:

Types
-----

Common Attributes
-----------------

Reserved Fields
---------------

Special Fields
--------------

.. [#rawsql] writing raw SQL queries is possible, but requires care as it
             bypasses all Odoo authentication and security mechanisms.
