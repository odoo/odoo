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

Although they are all expressed as XML and have common points (most commonly
the presence of ``<field>`` elements), each view has its own ``arch``
structure with a specific root elements, semantics and affordances.

Most views accept the ``create``, ``edit`` and ``delete`` attributes on their
root element, when applicable this is used to disable the corresponding action
from the view (hide the relevant buttons or avoid displaying an interface to
perform it). May be set to ``true`` or ``false``. Setting them to ``true``
will override their auto-generation from access-rights.

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
    respectively at the top or bottom of the list.

    The architecture for the inline :ref:`form view <reference/views/form>` is
    derived from the list view. Most attributes valid on a :ref:`form view
    <reference/views/form>`'s fields and buttons are thus accepted by list
    views although they may not have any meaning if the list view is
    non-editable
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

.. _reference/views/list/button:

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
    defines a column where the corresponding field should be displayed for
    each record. Can use the following attributes:

    ``name``
        the name of the field to display in the current model. A given name
        can only be used once per view
    ``string``
        the title of the field's column (by default, uses the ``string`` of
        the model's field)
    ``invisible``
        fetches and stores the field, but doesn't display the column in the
        table. Necessary for fields which shouldn't be displayed but are
        used by e.g. ``@colors``
    ``groups``
        lists the groups which should be able to see the field
    ``widget``
        alternate representations for a field's display. Possible list view
        values are:

        ``progressbar``
            displays ``float`` fields as a progress bar.
        ``many2onebutton``
            replaces the m2o field's value by a checkmark if the field is
            filled, and a cross if it is not
        ``handle``
            for ``sequence`` fields, instead of displaying the field's value
            just displays a dra&drop icon
    ``sum``, ``avg``
        displays the corresponding aggregate at the bottom of the column. The
        aggregation is only computed on *currently displayed* records. The
        aggregation operation must match the corresponding field's
        ``group_operator``
    ``attrs``
        dynamic attributes based on record values. Only effects the current
        field, so e.g. ``invisible`` will hide the field but leave the same
        field of other records visible, it will not hide the column itself

    .. note:: if the list view is ``editable``, any field attribute from the
              :ref:`form view <reference/views/form>` is also valid and will
              be used when setting up the inline form view

.. _reference/views/form:

Forms
-----

Form views are used to display the data from a single record. Their root
element is ``<form>``. They are composed of regular HTML_ with additional
structural and semantic components.

Structural components
'''''''''''''''''''''

Structural components provide structure or "visual" features with little
logic. They are used as elements or sets of elements in form views.

``notebook``
  defines a tabbed section. Each tab is defined through a ``page`` child
  element. Pages can have the following attributes:

  ``string`` (required)
    the title of the tab
  ``accesskey``
    an HTML accesskey_
  ``attrs``
    standard dynamic attributes based on record values

``group``
  used to define column layouts in forms. By default, groups define 2 columns
  and most direct children of groups take a single column. ``field`` direct
  children of groups display a label by default, and the label and the field
  itself have a colspan of 1 each.

  The number of columns in a ``group`` can be customized using the ``col``
  attribute, the number of columns taken by an element can be customized using
  ``colspan``.

  Children are laid out horizontally (tries to fill the next column before
  changing row).

  Groups can have a ``string`` attribute, which is displayed as the group's
  title
``newline``
  only useful within ``group`` elements, ends the current row early and
  immediately switches to a new row (without filling any remaining column
  beforehand)
``separator``
  small horizontal spacing, with a ``string`` attribute behaves as a section
  title
``sheet``
  can be used as a direct child to ``form`` for a narrower and more responsive
  form layout
``header``
  combined with ``sheet``, provides a full-width location above the sheet
  itself, generally used to display workflow buttons and status widgets

Semantic components
'''''''''''''''''''

Semantic components tie into and allow interaction with the Odoo
system. Available semantic components are:

``button``
  call into the Odoo system, similar to :ref:`list view buttons
  <reference/views/list/button>`
``field``
  renders (and allow edition of, possibly) a single field of the current
  record. Possible attributes are:

  ``name`` (mandatory)
    the name of the field to render
  ``widget``
    fields have a default rendering based on their type
    (e.g. :class:`~openerp.fields.Char`,
    :class:`~openerp.fields.Many2one`). The ``widget`` attributes allows using
    a different rendering method and context.

    .. todo:: list of widgets

       & options & specific attributes (e.g. widget=statusbar
       statusbar_visible statusbar_colors clickable)
  ``options``
    JSON object specifying configuration option for the field's widget
    (including default widgets)
  ``class``
    HTML class to set on the generated element, common field classes are:

    ``oe_inline``
      prevent the usual line break following fields
    ``oe_left``, ``oe_right``
      floats_ the field to the corresponding direction
    ``oe_read_only``, ``oe_edit_only``
      only displays the field in the corresponding form mode
    ``oe_no_button``
      avoids displaying the navigation button in a
      :class:`~openerp.fields.Many2one`
    ``oe_avatar``
      for image fields, displays images as "avatar" (square, 90x90 maximum
      size, some image decorations)
  ``groups``
    only displays the field for specific users
  ``on_change``
    calls the specified method when this field's value is edited, can generate
    update other fields or display warnings for the user

    .. deprecated:: 8.0

       Use :func:`openerp.api.onchange` on the model

  ``attrs``
    dynamic meta-parameters based on record values
  ``domain``
    for relational fields only, filters to apply when displaying existing
    records for selection
  ``context``
    for relational fields only, context to pass when fetching possible values
  ``readonly``
    display the field in both readonly and edition mode, but never make it
    editable
  ``required``
    generates an error and prevents saving the record if the field doesn't
    have a value
  ``nolabel``
    don't automatically display the field's label, only makes sense if the
    field is a direct child of a ``group`` element
  ``placeholder``
    help message to display in *empty* fields. Can replace field labels in
    complex forms. *Should not* be an example of data as users are liable to
    confuse placeholder text with filled fields
  ``mode``
    for :class:`~openerp.fields.One2many`, display mode (view type) to use for
    the field's linked records. One of ``tree``, ``form``, ``kanban`` or
    ``graph``. The default is ``tree`` (a list display)
  ``help``
    tooltip displayed for users when hovering the field or its label
  ``filename``
    for binary fields, name of the related field providing the name of the
    file
  ``password``
    indicates that a :class:`~openerp.fields.Char` field stores a password and
    that its data shouldn't be displayed

.. todo:: classes for forms

.. todo:: widgets?

.. _reference/views/graph:

Graphs
------

The graph view is used to visualize aggregations over a number of records or
record groups. Its root element is ``<graph>`` which can take the following
attributes:

``type``
  one of ``bar`` (default), ``pie``, ``line`` and ``pivot``, the type of graph
  to use (``pivot`` technically isn't a graph type, it displays the
  aggregation as a `pivot table`_)
``stacked``
  only used for ``bar`` charts. If present and set to ``True``, stacks bars
  within a group

The only allowed element within a graph view is ``field`` which can have the
following attributes:

``name`` (required)
  the name of a field to use in a graph view. If used for grouping (rather
  than aggregating), can be augmented with a
  :ref:`reference/views/graph/functions`

``type``
  indicates whether the field should be used as a grouping criteria or as an
  aggregated value within a group. Possible values are:

  ``row`` (default)
    groups by the specified field. All graph types support at least one level
    of grouping, some may support more. For pivot tables, each group gets its
    own row.
  ``col``
    only used by pivot tables, creates column-wise groups
  ``measure``
    field to aggregate within a group

.. warning::

   graph view aggregations are performed on database content, non-stored
   function fields can not be used in graph views

.. _reference/views/graph/functions:

Grouping function
'''''''''''''''''

Field names in graph views can be postfixed with a grouping function using the
form :samp:`{field_name}:{function}`. As of 8.0, only date and datetime fields
support grouping functions. The available grouping functions are ``day``,
``week``, ``month``, ``quarter`` and ``year``. By default, date and datetime
fields are grouped month-wise.

.. _reference/views/kanban:

Kanban
------

The kanban view is a `kanban board`_ visualisation: it displays records as
"cards", halfway between a :ref:`list view <reference/views/list>` and a
non-editable :ref:`form view <reference/views/form>`. Records may be grouped
in columns for use in workflow visualisation or manipulation (e.g. tasks or
work-progress management), or ungrouped (used simply to visualize records).

The root element of the Kanban view is ``<kanban>``, it can use the following
attributes:

``default_group_by``
  whether the kanban view should be grouped if no grouping is specified via
  the action or the current research. Should be the name of the field to group
  by when no grouping is otherwise specified
``default_order``
  cards sorting order used if the user has not already sorted the records (via
  the list view)
``class``
  adds HTML classes to the root HTML element of the Kanban view
``quick_create``
  whether it should be possible to create records without switching to the
  form view. By default, ``quick_create`` is enabled when the Kanban view is
  grouped, and disabled when not.

  Set to ``true`` to always enable it, and to ``false`` to always disable it.

Possible children of the view element are:

``field``
  declares fields to aggregate or to use in kanban *logic*. If the field is
  simply displayed in the kanban view, it does not need to be pre-declared.

  Possible attributes are:

  ``name`` (required)
    the name of the field to fetch
  ``sum``, ``avg``, ``min``, ``max``, ``count``
    displays the corresponding aggregation at the top of a kanban column, the
    field's value is the label of the aggregation (a string). Only one
    aggregate operation per field is supported.

``templates``
  defines a list of :ref:`reference/qweb` templates. Cards definition may be
  split into multiple templates for clarity, but kanban views *must* define at
  least one root template ``kanban-box``, which will be rendered once for each
  record.

  The kanban view uses mostly-standard :ref:`javascript qweb
  <reference/qweb/javascript>` and provides the following context variables:

  ``instance``
    the current :ref:`reference/javascript/client` instance
  ``widget``
    the current :js:class:`KanbanRecord`, can be used to fetch some
    meta-information. These methods are also available directly in the
    template context and don't need to be accessed via ``widget``
  ``record``
    an object with all the requested fields as its attributes. Each field has
    two attributes ``value`` and ``raw_value``, the former is formatted
    according to current user parameters, the latter is the direct value from
    a :meth:`~openerp.models.Model.read`
  ``read_only_mode``
    self-explanatory


    .. rubric:: buttons and fields

    While most of the Kanban templates are standard :ref:`reference/qweb`, the
    Kanban view processes ``field``, ``button`` and ``a`` elements specially:

    * by default fields are replaced by their formatted value, unless they
      match specific kanban view widgets

      .. todo:: list widgets?

    * buttons and links with a ``type`` attribute become perform Odoo-related
      operations rather than their standard HTML function. Possible types are:

      ``action``, ``object``
        standard behavior for :ref:`Odoo buttons
        <reference/views/list/button>`, most attributes relevant to standard
        Odoo buttons can be used.
      ``open``
        opens the card's record in the form view in read-only mode
      ``edit``
        opens the card's record in the form view in editable mode
      ``delete``
        deletes the card's record and removes the card

    .. todo::

       * kanban-specific CSS
       * kanban structures/widgets (vignette, details, ...)

Javascript API
''''''''''''''

.. js:class:: KanbanRecord

   :js:class:`Widget` handling the rendering of a single record to a
   card. Available within its own rendering as ``widget`` in the template
   context.

   .. js:function:: kanban_color(raw_value)

      Converts a color segmentation value to a kanban color class
      :samp:`oe_kanban_color_{color_index}`. The built-in CSS provides classes
      up to a ``color_index`` of 9.

   .. js:function:: kanban_getcolor(raw_value)

      Converts a color segmentation value to a color index (between 0 and 9 by
      default). Color segmentation values can be either numbers or strings.

   .. js:function:: kanban_image(model, field, id[, cache][, options])

      Generates the URL to the specified field as an image access.

      :param String model: model hosting the image
      :param String field: name of the field holding the image data
      :param id: identifier of the record contaning the image to display
      :param Number cache: caching duration (in seconds) of the browser
                           default should be overridden. ``0`` disables
                           caching entirely
      :returns: an image URL

   .. js:function:: kanban_text_ellipsis(string[, size=160])

      clips text beyond the specified size and appends an ellipsis to it. Can
      be used to display the initial part of potentially very long fields
      (e.g. descriptions) without the risk of unwieldy cards

.. _reference/views/calendar:

Calendar
--------

Calendar views display records as events in a daily, weekly or monthly
calendar. Their root element is ``<calendar>``. Available attributes on the
calendar view are:

``date_start`` (required)
    name of the record's field holding the start date for the event
``date_end``
    name of the record's field holding the end date for the event, if
    ``date_end`` is provided records become movable (via drag and drop)
    directly in the calendar
``date_delay``
    alternative to ``date_end``, provides the duration of the event instead of
    its end date

    .. todo:: what's the unit? Does it allow moving the record?

``color``
    name of a record field to use for *color segmentation*. Records in the
    same color segment are allocated the same highlight color in the calendar,
    colors are allocated semi-randomly.
``event_open_popup``
    opens the event in a dialog instead of switching to the form view, enabled
    by default
``quick_add``
    enables quick-event creation on click: only asks the user for a ``name``
    and tries to create a new event with just that and the clicked event
    time. Falls back to a full form dialog if the quick creation fails
``display``
    format string for event display, field names should be within brackets
    ``[`` and ``]``
``all_day``
    name of a boolean field on the record indicating whether the corresponding
    event is flagged as day-long (and duration is irrelevant)


.. todo::

   what's the purpose of ``<field>`` inside a calendar view?

.. todo::

   calendar code is an unreadable mess, no idea what these things are:

   * ``attendee``
   * ``avatar_model``
   * ``use_contacts``

   calendar code also seems to refer to multiple additional attributes of
   unknown purpose

.. _reference/views/gantt:

Gantt
-----

Gantt views appropriately display Gantt charts (for scheduling).

The root element of gantt views is ``<gantt/>``, it has no children but can
take the following attributes:

``date_start`` (required)
  name of the field providing the start datetime of the event for each
  record.
``date_stop``
  name of the field providing the end duration of the event for each
  record. Can be replaced by ``date_delay``. One (and only one) of
  ``date_stop`` and ``date_delay`` must be provided.

  If the field is ``False`` for a record, it's assumed to be a "point event"
  and the end date will be set to the start date
``date_delay``
  name of the field providing the duration of the event
``progress``
  name of a field providing the completion percentage for the record's event,
  between 0 and 100
``default_group_by``
  name of a field to group tasks by

.. previously documented content which don't seem to be used anymore:

   * string
   * day_length
   * color
   * mode
   * date_string
   * <level>
   * <field>
   * <html>

.. _reference/views/diagram:

Diagram
-------

The diagram view can be used to display directed graphs of records. The root
element is ``<diagram>`` and takes no attributes.

Possible children of the diagram view are:

``node`` (required, 1)
    Defines the nodes of the graph. Its attributes are:

    ``object``
      the node's Odoo model
    ``shape``
      conditional shape mapping similar to colors and fonts in :ref:`the list
      view <reference/views/list>`. The only valid shape is ``rectangle`` (the
      default shape is an ellipsis)
    ``bgcolor``
      same as ``shape``, but conditionally maps a background color for
      nodes. The default background color is white, the only valid alternative
      is ``grey``.
``arrow`` (required, 1)
    Defines the directed edges of the graph. Its attributes are:

    ``object`` (required)
      the edge's Odoo model
    ``source`` (required)
      :class:`~openerp.fields.Many2one` field of the edge's model pointing to
      the edge's source node record
    ``destination`` (required)
      :class:`~openerp.fields.Many2one` field of the edge's model pointing to
      the edge's destination node record
    ``label``
      Python list of attributes (as quoted strings). The corresponding
      attributes's values will be concatenated and displayed as the edge's
      label

``label``
    Explanatory note for the diagram, the ``string`` attribute defines the
    note's content. Each ``label`` is output as a paragraph in the diagram
    header, easily visible but without any special emphasis.

.. _reference/views/search:

Search
------

Search views are a break from previous view types in that they don't display
*content*: although they apply to a specific model, they are used to filter
other view's content (generally aggregated views
e.g. :ref:`reference/views/list` or :ref:`reference/views/graph`). Beyond that
difference in use case, they are defined the same way.

The root element of search views is ``<search>``. It takes no attributes.

.. @string is not displayed anywhere, should be removed

Possible children elements of the search view are:

``field``
    fields define domains or contexts with user-provided values. When search
    domains are generated, field domains are composed with one another and
    with filters using **AND**.

    Fields can have the following attributes:

    ``name``
        the name of the field to filter on
    ``string``
        the field's label
    ``operator``
        by default, fields generate domains of the form :samp:`[({name},
        {operator}, {provided_value})]` where ``name`` is the field's name and
        ``provided_value`` is the value provided by the user, possibly
        filtered or transformed (e.g. a user is expected to provide the
        *label* of a selection field's value, not the value itself).

        The ``operator`` attribute allows overriding the default operator,
        which depends on the field's type (e.g. ``=`` for float fields but
        ``ilike`` for char fields)
    ``filter_domain``
        complete domain to use as the field's search domain, can use a
        ``self`` variable to inject the provided value in the custom
        domain. Can be used to generate significantly more flexible domains
        than ``operator`` alone (e.g. searches on multiple fields at once)

        If both ``operator`` and ``filter_domain`` are provided,
        ``filter_domain`` takes precedence.
    ``context``
        allows adding context keys, including the user-provided value (which
        as for ``domain`` is available as a ``self`` variable). By default,
        fields don't generate domains.

        .. note:: the domain and context are inclusive and both are generated
                  if if a ``context`` is specified. To only generate context
                  values, set ``filter_domain`` to an empty list:
                  ``filter_domain="[]"``
    ``groups``
        make the field only available to specific users
    ``widget``
        use specific search widget for the field (the only use case in
        standard Odoo 8.0 is a ``selection`` widget for
        :class:`~openerp.fields.Many2one` fields)
    ``domain``
        if the field can provide an auto-completion
        (e.g. :class:`~openerp.fields.Many2one`), filters the possible
        completion results.

``filter``
    a filter is a predefined toggle in the search view, it can only be enabled
    or disabled. Its main purposes are to add data to the search context (the
    context passed to the data view for searching/filtering), or to append new
    sections to the search filter.

    Filters can have the following attributes:

    ``string`` (required)
        the label of the filter
    ``domain``
        an Odoo :ref:`domain <reference/orm/domains>`, will be appended to the
        action's domain as part of the search domain
    ``context``
        a Python dictionary, merged into the action's domain to generate the
        search domain
    ``name``
        logical name for the filter, can be used to :ref:`enable it by default
        <reference/views/search/defaults>`, can also be used as
        :ref:`inheritance hook <reference/views/inheritance>`
    ``help``
        a longer explanatory text for the filter, may be displayed as a
        tooltip
    ``groups``
        makes a filter only available to specific users
    ``icon``
        an icon to display next to the label, if there's sufficient space

        .. deprecated:: 7.0

    .. tip::

       .. versionadded:: 7.0

       Sequences of filters (without non-filters separating them) are treated
       as inclusively composited: they will be composed with ``OR`` rather
       than the usual ``AND``, e.g.

       .. code-block:: xml

          <filter domain="[('state', '=', 'draft')]"/>
          <filter domain="[('state', '=', 'done')]"/>

       if both filters are selected, will select the records whose ``state``
       is ``draft`` or ``done``, but

       .. code-block:: xml

          <filter domain="[('state', '=', 'draft')]"/>
          <separator/>
          <filter domain="[('delay', '<', 15)]"/>

       if both filters are selected, will select the records whose ``state``
       is ``draft`` **and** ``delay`` is below 15.

``separator``
    can be used to separates groups of filters in simple search views
``group``
    can be used to separate groups of filters, more readable than
    ``separator`` in complex search views

.. _reference/views/search/defaults:

Search defaults
'''''''''''''''

Search fields and filters can be configured through the action's ``context``
using :samp:`search_default_{name}` keys. For fields, the value should be the
value to set in the field, for filters it's a boolean value. For instance,
assuming ``foo`` is a field and ``bar`` is a filter an action context of::

  {
    'search_default_foo': 'acro',
    'search_default_bar': 1
  }

will automatically enable the ``bar`` filter and search the ``foo`` field for
*acro*.

.. _reference/views/qweb:

QWeb
----

QWeb views are standard :ref:`reference/qweb` templates inside a view's
``arch``. They don't have a specific root element.

A QWeb view can only contain a single template\ [#template_inherit]_, and the
template's name *must* match the view's complete (including module name)
:term:`external id`.

:ref:`reference/data/template` should be used as a shortcut to define QWeb
views.

.. [#hasclass] an extension function is added for simpler matching in QWeb
               views: ``hasclass(*classes)`` matches if the context node has
               all the specified classes
.. [#treehistory] for historical reasons, it has its origin in tree-type views
                  later repurposed to a more table/list-type display
.. [#template_inherit] or no template if it's an inherited view, then :ref:`it
                       should only contain xpath elements
                       <reference/views/inheritance>`

.. _accesskey: http://www.w3.org/TR/html5/editing.html#the-accesskey-attribute
.. _CSS color unit: http://www.w3.org/TR/css3-color/#colorunits
.. _floats: https://developer.mozilla.org/en-US/docs/Web/CSS/float
.. _HTML: http://en.wikipedia.org/wiki/HTML
.. _kanban board: http://en.wikipedia.org/wiki/Kanban_board
.. _pivot table: http://en.wikipedia.org/wiki/Pivot_table
.. _XPath: http://en.wikipedia.org/wiki/XPath
