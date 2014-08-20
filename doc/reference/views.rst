.. _reference/views:

=====
Views
=====

.. _reference/views/structure:

Structure
=========

View objects expose a number of fields, they are optional unless specified
otherwise)

``name`` (mandatory)
    only useful as a mnemonic/description of the view when looking for one in
    a list of some sort
``model``
    the model linked to the view, if applicable (it doesn't for QWeb views)
``priority``
    client programs can request views by ``id``, or by ``(model, type)``. For
    the latter, all the views for the right type and model will be looked for,
    and the one with the lowest ``priority`` number will be returned (it is
    the "default view").

    ``priority`` also defines the order of application during :ref:`view
    inheritance <reference/views/inheritance>`
``arch``
    the description of the view's layout, see
    :ref:`reference/views/architecture`
``groups_id``
    :class:`~openerp.fields.Many2many` field to the groups allowed to view/use
    the current view
``inherit_id``
    the current view's parent view, see :ref:`reference/views/inheritance`,
    unset by default
``mode``
    inheritance mode, see :ref:`reference/views/inheritance`. If
    ``inherit_id`` is unset the ``mode`` can only be ``primary``. If
    ``inherit_id`` is set, ``extension`` by default but can be explicitly set
    to ``primary``
``application``
    website feature defining togglable views. By default, views are always
    applied

.. _reference/views/inheritance:

Inheritance
===========

View matching
-------------

* if a view is requested by ``(model, type)``, the view with the right model
  and type, ``mode=primary`` and the lowest priority is matched
* when a view is requested by ``id``, if its mode is not ``primary`` its
  *closest* parent with mode ``primary`` is matched

View resolution
---------------

Resolution generates the final ``arch`` for a requested/matched ``primary``
view:

#. if the view has a parent, the parent is fully resolved then the current
   view's inheritance specs are applied
#. if the view has no parent, its ``arch`` is used as-is
#. the current view's children with mode ``extension`` are looked up  and their
   inheritance specs are applied depth-first (a child view is applied, then
   its children, then its siblings)

The result of applying children views yields the final ``arch``

Inheritance specs
-----------------

There are three types of inheritance specs:

* An ``xpath`` element with an ``expr`` attribute. ``expr`` is an XPath_
  expression\ [#hasclass]_ applied to the current ``arch``, the first node
  it finds is the match
* a ``field`` element with a ``name`` attribute, matches the first ``field``
  with the same ``name``
* any other element, the first element with the same name and identical
  attributes (ignoring ``position``) is matched

The inheritance spec can an optional ``position`` attribute specifhing how
the matched node should be altered:

``inside`` (default)
    the content of the inheritance spec is appended to the matched node
``replace``
    the content of the inheritance spec replaces the matched node
``after``
    the content of the inheritance spec is added to the matched node's
    parent, after the matched node
``before``
    the content of the inheritance spec is added to the matched node's
    parent, before the matched node
``attribute``
    the content of the inheritance spec should be ``attribute`` elements
    with a ``name`` attribute and an optional body:

    * if the ``attribute`` element has a body, a new attributed named
      after its ``name`` is created on the matched node with the
      ``attribute`` element's text as value
    * if the ``attribute`` element has no body, the attribute named after
      its ``name`` is removed from the matched node. If no such attribute
      exists, an error is raised

A view's specs are applied sequentially.

.. _reference/views/architecture:

Architecture structures
=======================

.. _reference/views/list:

Lists
-----

The root element of list views is ``<tree>``\ [#treehistory]_. The list view's
root can have the following attributes:

``editable``
    by default, selecting a list view's row opens the corresponding
    :ref:`form view <reference/views/form>`. The ``editable`` attributes makes
    the list view itself editable in-place.

    Valid values are ``top`` and ``bottom``, making *new* records appear
    respectively at the top or bottom of the list
``colors``
    allows changing the color of a row's text based on the corresponding
    record's attributes.

    Defined as a mapping of colors to Python expressions. Values are of the
    form: :samp:`{color}:{expr}[;...]`. For each record, pairs are tested
    in-order, the expression is evaluated for the record and if ``true`` the
    corresponding color is applied to the row. If no color matches, uses the
    default text color (black).

    * ``color`` can be any valid `CSS color unit`_.
    * ``expr`` should be a Python expression evaluated with the current
      record's attributes as context values. Other context values are ``uid``
      (the id of the current user) and ``current_date`` (the current date as
      a string of the form ``yyyy-MM-dd``)
``fonts``
    allows changing a row's font style based on the corresponding record's
    attributes.

    The format is the same as for ``color``, but the ``color`` of each pair
    is replaced by ``bold``, ``italic`` or ``underline``, the expression
    evaluating to ``true`` will apply the corresponding style to the row's
    text. Contrary to ``colors``, multiple pairs can match each record
``create``, ``edit``, ``delete``
    allows *dis*\ abling the corresponding action in the view by setting the
    corresponding attribute to ``false``
``on_write``
    only makes sense on an ``editable`` list. Should be the name of a method
    on the list's model. The method will be called with the ``id`` of a record
    after having created or edited that record (in database).

    The method should return a list of ids of other records to load or update.
``string``
    alternative translatable label for the view

    .. deprecated:: 8.0

        not displayed anymore

.. toolbar attribute is for tree-tree views

Possible children elements of the list view are:

``button``
    displays a button in a list cell

    ``icon``
        icon to use to display the button
    ``string``
        * if there is no ``icon``, the button's text
        * if there is an ``icon``, ``alt`` text for the icon
    ``type``
        type of button, indicates how it clicking it affects Odoo:

        ``workflow`` (default)
            sends a signal to a workflow. The button's ``name`` is the
            workflow signal, the row's record is passed as argument to the
            signal
        ``object``
            call a method on the list's model. The button's ``name`` is the
            method, which is called with the current row's record id and the
            current context.

            .. web client also supports a @args, which allows providing
               additional arguments as JSON. Should that be documented? Does
               not seem to be used anywhere

        ``action``
            load an execute an ``ir.actions``, the button's ``name`` is the
            database id of the action. The context is expanded with the list's
            model (as ``active_model``), the current row's record
            (``active_id``) and all the records currently loaded in the list
            (``active_ids``, may be just a subset of the database records
            matching the current search)
    ``name``
        see ``type``
    ``args``
        see ``type``
    ``attrs``
        dynamic attributes based on record values.

        A mapping of attributes to domains, domains are evaluated in the
        context of the current row's record, if ``True`` the corresponding
        attribute is set on the cell.

        Possible attributes are ``invisible`` (hides the button) and
        ``readonly`` (disables the button but still shows it)
    ``states``
        shorthand for ``invisible`` ``attrs``: a list of space, separated
        states, requires that the model has a ``state`` field and that it is
        used in the view.

        Makes the button ``invisible`` if the record is *not* in one of the
        listed states
    ``context``
        merged into the view's context when performing the button's Odoo call
    ``confirm``
        confirmation message to display (and for the user to accept) before
        performing the button's Odoo call

    .. declared but unused: help

``field``
    displays a field's value in a list cell

.. _reference/views/form:

Forms
-----

.. _reference/views/search:

Search
------

.. _reference/views/graphs:

Graphs
------

@type=row/@type=col

.. _reference/views/kanban:

Kanban
------

.. _reference/views/calendar:

Calendar
--------

.. _reference/views/qweb:

QWeb (?)
--------

.. [#hasclass] an extension function is added for simpler matching in QWeb
               views: ``hasclass(*classes)`` matches if the context node has
               all the specified classes
.. [#treehistory] for historical reasons, it has its origin in tree-type views
                  later repurposed to a more table/list-type display

.. _CSS color unit: http://www.w3.org/TR/css3-color/#colorunits
.. _XPath: http://en.wikipedia.org/wiki/XPath
