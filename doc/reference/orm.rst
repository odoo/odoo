.. _reference/orm:

===
ORM
===

.. _reference/orm/model:

Model
=====

.. - can't get autoattribute to import docstrings, so use regular attribute
   - no autoclassmethod

.. currentmodule:: openerp.models

.. autoclass:: openerp.models.Model

    .. rubric:: Structural attributes

    .. attribute:: _name

        business object name, in dot-notation (in module namespace)

    .. attribute:: _rec_name

        Alternative field to use as name, used by osv’s name_get()
        (default: ``'name'``)

    .. attribute:: _inherit

        * If :attr:`._name` is set, names of parent models to inherit from.
          Can be a ``str`` if inheriting from a single parent
        * If :attr:`._name` is unset, name of a single model to extend
          in-place

    .. attribute:: _order

        Ordering field when searching without an ordering specified (default:
        ``'id'``)

        :type: str

    .. attribute:: _auto

        Whether a database table should be created (default: ``True``)

        If set to ``False``, override :meth:`.init` to create the database
        table

    .. attribute:: _inherits

        dictionary mapping the _name of the parent business objects to the
        names of the corresponding foreign key fields to use

    .. attribute:: _constraints

        list of ``(constraint_function, message, fields)`` defining Python
        constraints. The fields list is indicative

    .. attribute:: _sql_constraints

        list of ``(name, sql_definition, message)`` triples defining SQL
        constraints to execute when generating the backing table

    .. rubric:: CRUD

    .. automethod:: create
    .. automethod:: browse
    .. automethod:: unlink
    .. automethod:: write

    .. automethod:: read

    .. rubric:: Research

    .. automethod:: search
    .. automethod:: search_count
    .. automethod:: name_search

    .. rubric:: Recordset operations

    .. autoattribute:: ids
    .. automethod:: ensure_one
    .. automethod:: exists
    .. automethod:: filtered
    .. automethod:: sorted
    .. automethod:: update

    .. rubric:: Environment swapping

    .. automethod:: sudo
    .. automethod:: with_context
    .. automethod:: with_env

    .. rubric:: ???

    .. automethod:: default_get
    .. automethod:: copy
    .. automethod:: add_default_value
    .. automethod:: name_get
    .. automethod:: name_create
    .. automethod:: new

    .. rubric:: Automatic fields

    .. attribute:: id

        Identifier :class:`field <openerp.fields.Field>`

    .. attribute:: _log_access

        Whether log access fields (``create_date``, ``write_uid``, ...) should
        be generated (default: ``True``)

    .. attribute:: create_date

        Date at which the record was created

        :type: :class:`~openerp.field.Datetime`

    .. attribute:: create_uid

        Relational field to the user who created the record

        :type: ``res.users``

    .. attribute:: write_date

        Date at which the record was last modified

        :type: :class:`~openerp.field.Datetime`

    .. attribute:: write_uid

        Relational field to the last user who modified the record

        :type: ``res.users``

.. _reference/orm/decorators:

Method decorators
=================

.. automodule:: openerp.api
    :members: one, multi, model, depends, constrains, onchange, returns

.. _reference/orm/fields:

Fields
======

.. _reference/orm/fields/basic:

Basic fields
------------

.. autodoc documents descriptors as attributes, even for the *definition* of
   descriptors. As a result automodule:: openerp.fields lists all the field
   classes as attributes without providing inheritance info or methods (though
   we don't document methods as they're not useful for "external" devs)
   (because we don't support pluggable field types) (or do we?)

.. autoclass:: openerp.fields.Field

.. autoclass:: openerp.fields.Char
    :show-inheritance:

.. autoclass:: openerp.fields.Boolean
    :show-inheritance:

.. autoclass:: openerp.fields.Integer
    :show-inheritance:

.. autoclass:: openerp.fields.Float
    :show-inheritance:

.. autoclass:: openerp.fields.Text
    :show-inheritance:

.. autoclass:: openerp.fields.Selection
    :show-inheritance:

.. autoclass:: openerp.fields.Html
    :show-inheritance:

.. autoclass:: openerp.fields.Date
    :show-inheritance:

.. autoclass:: openerp.fields.Datetime
    :show-inheritance:

.. _reference/orm/fields/relational:

Relational fields
-----------------

.. autoclass:: openerp.fields.Many2one
    :show-inheritance:

.. autoclass:: openerp.fields.One2many
    :show-inheritance:

.. autoclass:: openerp.fields.Many2many
    :show-inheritance:

.. autoclass:: openerp.fields.Reference
    :show-inheritance:

.. _reference/orm/domains:

Domains
=======

A domain is a list of criterion, each criterion being a triple (either a
``list`` or a ``tuple``) of ``(field_name, operator, value)`` where:

``field_name`` (``str``)
    a field name of the current model, or a relationship traversal through
    a :class:`~openerp.fields.Many2one` using dot-notation e.g. ``'street'``
    or ``'partner_id.country'``
``operator`` (``str``)
    a comparison operator between the criterion's field and value.

    .. todo:: list and detail operators, original list is way incomplete
``value``
    variable type, must be comparable (through ``operator``) to the named
    field

Domain criteria can be combined using logical operators in *prefix* form:

``'&'``
    logical *AND*, default operation to combine criteria following one
    another. Arity 2 (uses the next 2 criteria or combinations).
``'|'``
    logical *OR*, arity 2.
``'!'``
    logical *NOT*, arity 1.

    .. tip:: Mostly to negate combinations of criteria
        :class: aphorism

        Individual criterion generally have a negative form (e.g. ``=`` ->
        ``!=``, ``<`` -> ``>=``) which is simpler than negating the positive.

.. admonition:: Example

    To search for partners named *ABC*, from belgium or germany, whose language
    is not english::

        [('name','=','ABC'),
         ('language.code','!=','en_US'),
         '|',('country_id.code','=','be'),
             ('country_id.code','=','de')]

    This domain is interpreted as:

    .. code-block:: text

            (name is 'ABC')
        AND (language is NOT english)
        AND (country is Belgium OR Germany)

