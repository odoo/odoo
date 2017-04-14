:banner: banners/data_files.jpg

.. _reference/data:

==========
Data Files
==========

Odoo is greatly data-driven, and a big part of modules definition is thus
the definition of the various records it manages: UI (menus and views),
security (access rights and access rules), reports and plain data are all
defined via records.

Structure
=========

The main way to define data in Odoo is via XML data files: The broad structure
of an XML data file is the following:

* Any number of operation elements within the root element ``odoo``

.. code-block:: xml

    <!-- the root elements of the data file -->
    <odoo>
      <operation/>
      ...
    </odoo>

Data files are executed sequentially, operations can only refer to the result
of operations defined previously

Core operations
===============

.. _reference/data/record:

``record``
----------

``record`` appropriately defines or updates a database record, it has the
following attributes:

``model`` (required)
    name of the model to create (or update)
``id``
    the :term:`external identifier` for this record. It is strongly
    recommended to provide one

    * for record creation, allows subsequent definitions to either modify or
      refer to this record
    * for record modification, the record to modify
``context``
    context to use when creating the record
``forcecreate``
    in update mode whether the record should be created if it doesn't exist

    Requires an :term:`external id`, defaults to ``True``.

``field``
----------

Each record can be composed of ``field`` tags, defining values to set when
creating the record. A ``record`` with no ``field`` will use all default
values (creation) or do nothing (update).

A ``field`` has a mandatory ``name`` attribute, the name of the field to set,
and various methods to define the value itself:

Nothing
    if no value is provided for the field, an implicit ``False`` will be set
    on the field. Can be used to clear a field, or avoid using a default value
    for the field.
``search``
    for :ref:`relational fields <reference/orm/fields/relational>`, should be
    a :ref:`domain <reference/orm/domains>` on the field's model.

    Will evaluate the domain, search the field's model using it and set the
    search's result as the field's value. Will only use the first result if
    the field is a :class:`~odoo.fields.Many2one`
``ref``
    if a ``ref`` attribute is provided, its value must be a valid
    :term:`external id`, which will be looked up and set as the field's value.

    Mostly for :class:`~odoo.fields.Many2one` and
    :class:`~odoo.fields.Reference` fields
``type``
    if a ``type`` attribute is provided, it is used to interpret and convert
    the field's content. The field's content can be provided through an
    external file using the ``file`` attribute, or through the node's body.

    Available types are:

    ``xml``, ``html``
        extracts the ``field``'s children as a single document, evaluates
        any :term:`external id` specified with the form ``%(external_id)s``.
        ``%%`` can be used to output actual *%* signs.
    ``file``
        ensures that the field content is a valid file path in the current
        model, saves the pair :samp:`{module},{path}` as the field value
    ``char``
        sets the field content directly as the field's value without
        alterations
    ``base64``
        base64_-encodes the field's content, useful combined with the ``file``
        *attribute* to load e.g. image data into attachments
    ``int``
        converts the field's content to an integer and sets it as the field's
        value
    ``float``
        converts the field's content to a float and sets it as the field's
        value
    ``list``, ``tuple``
        should contain any number of ``value`` elements with the same
        properties as ``field``, each element resolves to an item of a
        generated tuple or list, and the generated collection is set as the
        field's value
``eval``
    for cases where the previous methods are unsuitable, the ``eval``
    attributes simply evaluates whatever Python expression it is provided and
    sets the result as the field's value.

    The evaluation context contains various modules (``time``, ``datetime``,
    ``timedelta``, ``relativedelta``), a function to resolve :term:`external
    identifiers` (``ref``) and the model object for the current field if
    applicable (``obj``)

``delete``
----------

The ``delete`` tag can remove any number of records previously defined. It
has the following attributes:

``model`` (required)
    the model in which a specified record should be deleted
``id``
    the :term:`external id` of a record to remove
``search``
    a :ref:`domain <reference/orm/domains>` to find records of the model to
    remove

``id`` and ``search`` are exclusive

``function``
------------

The ``function`` tag calls a method on a model, with provided parameters.
It has two mandatory parameters ``model`` and ``name`` specifying respectively
the model and the name of the method to call.

Parameters can be provided using ``eval`` (should evaluate to a sequence of
parameters to call the method with) or ``value`` elements (see ``list``
values).

.. ignored assert

Shortcuts
=========

Because some important structural models of Odoo are complex and involved,
data files provide shorter alternatives to defining them using
:ref:`record tags <reference/data/record>`:

``menuitem``
------------

Defines an ``ir.ui.menu`` record with a number of defaults and fallbacks:

Parent menu
    * If a ``parent`` attribute is set, it should be the :term:`external id`
      of an other menu item, used as the new item's parent
    * If no ``parent`` is provided, tries to interpret the ``name`` attribute
      as a ``/``-separated sequence of menu names and find a place in the menu
      hierarchy. In that interpretation, intermediate menus are automatically
      created
    * Otherwise the menu is defined as a "top-level" menu item (*not* a menu
      with no parent)
Menu name
    If no ``name`` attribute is specified, tries to get the menu name from
    a linked action if any. Otherwise uses the record's ``id``
Groups
    A ``groups`` attribute is interpreted as a comma-separated sequence of
    :term:`external identifiers` for ``res.groups`` models. If an
    :term:`external identifier` is prefixed with a minus (``-``), the group
    is *removed* from the menu's groups
``action``
    if specified, the ``action`` attribute should be the :term:`external id`
    of an action to execute when the menu is open
``id``
    the menu item's :term:`external id`

.. _reference/data/template:

``template``
------------

Creates a :ref:`QWeb view <reference/views/qweb>` requiring only the ``arch``
section of the view, and allowing a few *optional* attributes:

``id``
    the view's :term:`external identifier`
``name``, ``inherit_id``, ``priority``
    same as the corresponding field on ``ir.ui.view`` (nb: ``inherit_id``
    should be an :term:`external identifier`)
``primary``
    if set to ``True`` and combined with a ``inherit_id``, defines the view
    as a primary
``groups``
    comma-separated list of group :term:`external identifiers`
``page``
    if set to ``"True"``, the template is a website page (linkable to,
    deletable)
``optional``
    ``enabled`` or ``disabled``, whether the view can be disabled (in the
    website interface) and its default status. If unset, the view is always
    enabled.

``report``
----------

Creates a ``ir.actions.report.xml`` record with a few default values.

Mostly just proxies attributes to the corresponding fields on
``ir.actions.report.xml``, but also automatically creates the item in the
:guilabel:`More` menu of the report's ``model``.

.. ignored url, act_window and ir_set

CSV data files
==============

XML data files are flexible and self-descriptive, but very verbose when
creating a number of simple records of the same model in bulk.

For this case, data files can also use csv_, this is often the case for
:ref:`access rights <reference/security/acl>`:

* the file name is :file:`{model_name}.csv`
* the first row lists the fields to write, with the special field ``id``
  for :term:`external identifiers` (used for creation or update)
* each row thereafter creates a new record

Here's the first lines of the data file defining US states
``res.country.state.csv``

.. literalinclude:: ../../odoo/addons/base/res/res.country.state.csv
    :language: text
    :lines: 1-15

rendered in a more readable format:

.. csv-table::
    :file: ../../odoo/addons/base/res/res.country.state.csv
    :header-rows: 1
    :class: table-striped table-hover table-condensed

For each row (record):

* the first column is the :term:`external id` of the record to create or
  update
* the second column is the :term:`external id` of the country object to link
  to (country objects must have been defined beforehand)
* the third column is the ``name`` field for ``res.country.state``
* the fourth column is the ``code`` field for ``res.country.state``

.. _base64: http://tools.ietf.org/html/rfc3548.html#section-3
.. _csv: http://en.wikipedia.org/wiki/Comma-separated_values
