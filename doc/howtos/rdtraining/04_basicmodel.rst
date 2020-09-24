.. _howto/rdtraining/04_basicmodel:

===============================
Part 4: Models And Basic Fields
===============================

At the end of the :ref:`previous chapter <howto/rdtraining/03_newapp>`, we were able to create an Odoo
module. However, at this point it is still an empty shell which doesn't allow us to store any data.
In our real estate module, we want to store the information related to the properties
(name, description, price, living area...) in a database. The Odoo framework provides tools to
facilitate the interaction with the database.

Before moving forward on the excercise, make sure the ``estate`` module is installed, i.e. it
must appear as 'Installed' in the Apps list.

Object-Relational Mapping
=========================

**Reference**: the documentation related to this topic can be found in the
:ref:`reference/orm/model` API.

.. note::

    **Goal**: at the end of this section, the table ``estate_property`` is created:

    .. code-block:: text

        $ psql -d rd-demo
        rd-demo=# SELECT COUNT(*) FROM estate_property;
        count
        -------
            0
        (1 row)

A key component of Odoo is the `ORM`_ layer.
This layer avoids having to write most `SQL`_
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

``-u estate`` means that we want to upgrade the ``estate`` module, i.e. the ORM will
apply on database schema changes. In this case, it creates a new table. ``-d rd-demo`` means
that the upgrade should be performed on the ``rd-demo`` database. ``-u`` should always be used in
combination with ``-d``.

During the startup, you should see the following warnings:

.. code-block:: text

    ...
    WARNING rd-demo odoo.models: The model estate.property has no _description
    ...
    WARNING rd-demo odoo.modules.loading: The model estate.property has no access rules, consider adding one...
    ...

If this is the case, then you should be good! To be sure, double check with ``psql`` as suggested in
the **Goal**.

.. exercise:: Add a description

    Add a ``_description`` to your model to get rid of one of the warnings.

Model fields
============

**Reference**: the documentation related to this topic can be found in the
:ref:`reference/orm/fields` API.

Fields are used to define what the model can store and where. Fields are
defined as attributes on the model class::

    from odoo import fields, models

    class TestModel(models.Model):
        _name = "test.model"
        _description = "Test Model"

        name = fields.Char()

The ``name`` field is a :class:`~odoo.fields.Char` which will be represented as a Python
``unicode`` and a SQL ``VARCHAR``.

Types
-----

.. note::

    **Goal**: at the end of this section, several basic fields are added to the table
    ``estate_property``:

    .. code-block:: text

        $ psql -d rd-demo

        rd-demo=# \d estate_property;
                                                    Table "public.estate_property"
            Column       |            Type             | Collation | Nullable |                   Default
        --------------------+-----------------------------+-----------+----------+---------------------------------------------
        id                 | integer                     |           | not null | nextval('estate_property_id_seq'::regclass)
        create_uid         | integer                     |           |          |
        create_date        | timestamp without time zone |           |          |
        write_uid          | integer                     |           |          |
        write_date         | timestamp without time zone |           |          |
        name               | character varying           |           |          |
        description        | text                        |           |          |
        postcode           | character varying           |           |          |
        date_availability  | date                        |           |          |
        expected_price     | double precision            |           |          |
        selling_price      | double precision            |           |          |
        bedrooms           | integer                     |           |          |
        living_area        | integer                     |           |          |
        facades            | integer                     |           |          |
        garage             | boolean                     |           |          |
        garden             | boolean                     |           |          |
        garden_area        | integer                     |           |          |
        garden_orientation | character varying           |           |          |
        Indexes:
            "estate_property_pkey" PRIMARY KEY, btree (id)
        Foreign-key constraints:
            "estate_property_create_uid_fkey" FOREIGN KEY (create_uid) REFERENCES res_users(id) ON DELETE SET NULL
            "estate_property_write_uid_fkey" FOREIGN KEY (write_uid) REFERENCES res_users(id) ON DELETE SET NULL


There are two broad categories of fields: 'simple' fields which are atomic
values stored directly in the model's table and 'relational' fields linking
records (of the same model or of different models).

Example of simple fields are :class:`~odoo.fields.Boolean`, :class:`~odoo.fields.Float`,
:class:`~odoo.fields.Char`, :class:`~odoo.fields.Text`, :class:`~odoo.fields.Date`
or :class:`~odoo.fields.Selection`.

.. exercise:: Add basic fields to the Real Estate Property table

    Add the following basic fields to the table:

    ========================= =========================
    Field                     Type
    ========================= =========================
    name                      Char
    description               Text
    postcode                  Char
    date_availability         Date
    expected_price            Float
    selling_price             Float
    bedrooms                  Integer
    living_area               Integer
    facades                   Integer
    garage                    Boolean
    garden                    Boolean
    garden_area               Integer
    garden_orientation        Selection
    ========================= =========================

    The ``garden_orientation`` fields must have 4 options: 'North', 'South', 'East' and 'West'. The
    selection list is defined as a list of tuples, see
    `here <https://github.com/odoo/odoo/blob/b0e0035b585f976e912e97e7f95f66b525bc8e43/addons/crm/report/crm_activity_report.py#L31-L34>`__
    for example.

When the fields are added to the model, restart the server with ``-u estate``

.. code-block:: console

    $ ./odoo-bin --addons-path=../custom,../enterprise/,addons -d rd-demo -u estate

Connect to ``psql`` and check the structure of the table ``estate_property``. You'll notice that
a couple of of extra fields were also added to the table. We will come back to them later.

Common Attributes
-----------------

.. note::

    **Goal**: at the end of this section, the fields ``name`` and ``expected_price`` should be
    not nullable in the table ``estate_property``:

    .. code-block:: console

        rd-demo=# \d estate_property;
                                                    Table "public.estate_property"
            Column       |            Type             | Collation | Nullable |                   Default
        --------------------+-----------------------------+-----------+----------+---------------------------------------------
        ...
        name               | character varying           |           | not null |
        ...
        expected_price     | double precision            |           | not null |
        ...

Much like the model itself, its fields can be configured by passing
configuration attributes as parameters::

    name = field.Char(required=True)

Some attributes are available on all fields, here are the most common ones:

:attr:`~odoo.fields.Field.string` (``unicode``, default: field's name)
    The label of the field in UI (visible by users).
:attr:`~odoo.fields.Field.required` (``bool``, default: ``False``)
    If ``True``, the field can not be empty, it must either have a default
    value or always be given a value when creating a record.
:attr:`~odoo.fields.Field.help` (``unicode``, default: ``''``)
    Long-form, provides a help tooltip to users in the UI.
:attr:`~odoo.fields.Field.index` (``bool``, default: ``False``)
    Requests that Odoo create a `database index`_ on the column.

.. exercise:: Set attributes to existing fields.

    Add the following attributes:

    ========================= =========================
    Field                     Attribute
    ========================= =========================
    name                      required
    expected_price            required
    ========================= =========================

After restarting the server, both fields should be not nullable.

Automatic Fields
----------------

**Reference**: the documentation related to this topic can be found in
:ref:`reference/fields/automatic`.

As noticed previously, extra fields were added to the table ``estate_property``.
Odoo creates a few fields in all models\ [#autofields]_. These fields are
managed by the system and shouldn't be written to. They can be read if
useful or necessary:

:attr:`~odoo.fields.Model.id` (:class:`~odoo.fields.Id`)
    The unique identifier for a record in its model.
:attr:`~odoo.fields.Model.create_date` (:class:`~odoo.fields.Datetime`)
    Creation date of the record.
:attr:`~odoo.fields.Model.create_uid` (:class:`~odoo.fields.Many2one`)
    User who created the record.
:attr:`~odoo.fields.Model.write_date` (:class:`~odoo.fields.Datetime`)
    Last modification date of the record.
:attr:`~odoo.fields.Model.write_uid` (:class:`~odoo.fields.Many2one`)
    user who last modified the record.


Now that we have created our first table, let's
:ref:`add some security <howto/rdtraining/05_securityintro>`!


.. [#autofields] it is possible to :ref:`disable the automatic creation of some
                 fields <reference/fields/automatic/log_access>`
.. [#rawsql] writing raw SQL queries is possible, but requires care as it
             bypasses all Odoo authentication and security mechanisms.

.. _database index:
    http://use-the-index-luke.com/sql/preface
.. _ORM:
    https://en.wikipedia.org/wiki/Object-relational_mapping
.. _SQL:
    https://en.wikipedia.org/wiki/SQL
