:banner: banners/views.jpg

.. highlight:: xml
.. _reference/views:

=====
Views
=====

.. _reference/views/structure:

Common Structure
================

View objects expose a number of fields, they are optional unless specified
otherwise.

``name`` (mandatory)
    only useful as a mnemonic/description of the view when looking for one in
    a list of some sort
``model``
    the model linked to the view, if applicable (it doesn't for QWeb views)
``priority``
    client programs can request views by ``id``, or by ``(model, type)``. For
    the latter, all the views for the right type and model will be searched,
    and the one with the lowest ``priority`` number will be returned (it is
    the "default view").

    ``priority`` also defines the order of application during :ref:`view
    inheritance <reference/views/inheritance>`
``arch``
    the description of the view's layout
``groups_id``
    :class:`~odoo.fields.Many2many` field to the groups allowed to view/use
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

Inheritance specs are comprised of an element locator, to match
the inherited element in the parent view, and children element that
will be used to modify the inherited element.

There are three types of element locators for matching a target element:

* An ``xpath`` element with an ``expr`` attribute. ``expr`` is an XPath_
  expression\ [#hasclass]_ applied to the current ``arch``, the first node
  it finds is the match
* a ``field`` element with a ``name`` attribute, matches the first ``field``
  with the same ``name``. All other attributes are ignored during matching
* any other element: the first element with the same name and identical
  attributes (ignoring ``position`` and ``version`` attributes) is matched

The inheritance spec may have an optional ``position`` attribute specifying
how the matched node should be altered:

``inside`` (default)
    the content of the inheritance spec is appended to the matched node
``replace``
    the content of the inheritance spec replaces the matched node.
    Any text node containing only ``$0`` within the contents of the spec will
    be replaced  by a complete copy of the matched node, effectively wrapping
    the matched node.
``after``
    the content of the inheritance spec is added to the matched node's
    parent, after the matched node
``before``
    the content of the inheritance spec is added to the matched node's
    parent, before the matched node
``attributes``
    the content of the inheritance spec should be ``attribute`` elements
    with a ``name`` attribute and an optional body:

    * if the ``attribute`` element has a body, a new attributed named
      after its ``name`` is created on the matched node with the
      ``attribute`` element's text as value
    * if the ``attribute`` element has no body, the attribute named after
      its ``name`` is removed from the matched node. If no such attribute
      exists, an error is raised

A view's specs are applied sequentially.

.. _reference/views/list:

Lists
=====

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
``default_order``
    overrides the ordering of the view, replacing the model's default order.
    The value is a comma-separated list of fields, postfixed by ``desc`` to
    sort in reverse order:

    .. code-block:: xml

        <tree default_order="sequence,name desc">
``colors``
    .. deprecated:: 9.0
        replaced by ``decoration-{$name}``
``fonts``
    .. deprecated:: 9.0
        replaced by ``decoration-{$name}``
``decoration-{$name}``
    allow changing the style of a row's text based on the corresponding
    record's attributes.

    Values are Python expressions. For each record, the expression is evaluated
    with the record's attributes as context values and if ``true``, the
    corresponding style is applied to the row. Other context values are
    ``uid`` (the id of the current user) and ``current_date`` (the current date
    as a string of the form ``yyyy-MM-dd``).

    ``{$name}`` can be ``bf`` (``font-weight: bold``), ``it``
    (``font-style: italic``), or any `bootstrap contextual color
    <https://getbootstrap.com/docs/3.3/components/#available-variations>`_ (``danger``,
    ``info``, ``muted``, ``primary``, ``success`` or ``warning``).
``create``, ``edit``, ``delete``
    allows *dis*\ abling the corresponding action in the view by setting the
    corresponding attribute to ``false``
``limit``
    the default size of a page. It should be a positive integer
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

        Possible attribute is ``invisible`` (hides the button).
    ``states``
        shorthand for ``invisible`` ``attrs``: a list of states, comma separated,
        requires that the model has a ``state`` field and that it is
        used in the view.

        Makes the button ``invisible`` if the record is *not* in one of the
        listed states

        .. danger::

            Using ``states`` in combination with ``attrs`` may lead to
            unexpected results as domains are combined with a logical AND.
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
            just displays a drag&drop icon
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
=====

Form views are used to display the data from a single record. Their root
element is ``<form>``. They are composed of regular HTML_ with additional
structural and semantic components.

Structural components
---------------------

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
-------------------

Semantic components tie into and allow interaction with the Odoo
system. Available semantic components are:

``button``
  call into the Odoo system, similar to :ref:`list view buttons
  <reference/views/list/button>`. In addition, the following attribute can be
  specified:

  ``special``
    for form views opened in dialogs: ``save`` to save the record and close the
    dialog, ``cancel`` to close the dialog without saving.

``field``
  renders (and allow edition of, possibly) a single field of the current
  record. Possible attributes are:

  ``name`` (mandatory)
    the name of the field to render
  ``widget``
    fields have a default rendering based on their type
    (e.g. :class:`~odoo.fields.Char`,
    :class:`~odoo.fields.Many2one`). The ``widget`` attributes allows using
    a different rendering method and context.

    .. todo:: list of widgets

       & options & specific attributes (e.g. widget=statusbar
       statusbar_visible clickable)
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
      :class:`~odoo.fields.Many2one`
    ``oe_avatar``
      for image fields, displays images as "avatar" (square, 90x90 maximum
      size, some image decorations)
  ``groups``
    only displays the field for specific users
  ``on_change``
    calls the specified method when this field's value is edited, can generate
    update other fields or display warnings for the user

    .. deprecated:: 8.0

       Use :func:`odoo.api.onchange` on the model

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
    for :class:`~odoo.fields.One2many`, display mode (view type) to use for
    the field's linked records. One of ``tree``, ``form``, ``kanban`` or
    ``graph``. The default is ``tree`` (a list display)
  ``help``
    tooltip displayed for users when hovering the field or its label
  ``filename``
    for binary fields, name of the related field providing the name of the
    file
  ``password``
    indicates that a :class:`~odoo.fields.Char` field stores a password and
    that its data shouldn't be displayed

.. todo:: classes for forms

.. todo:: widgets?

Business Views guidelines
-------------------------

.. sectionauthor:: Aline Preillon, Raphael Collet

Business views are targeted at regular users, not advanced users.  Examples
are: Opportunities, Products, Partners, Tasks, Projects, etc.

.. image:: forms/oppreadonly.png
   :class: img-responsive

In general, a business view is composed of

1. a status bar on top (with technical or business flow),
2. a sheet in the middle (the form itself),
3. a bottom part with History and Comments.

Technically, the new form views are structured as follows in XML::

    <form>
        <header> ... content of the status bar  ... </header>
        <sheet>  ... content of the sheet       ... </sheet>
        <div class="oe_chatter"> ... content of the bottom part ... </div>
    </form>

The Status Bar
''''''''''''''

The purpose of the status bar is to show the status of the current record and
the action buttons.

.. image:: forms/status.png
   :class: img-responsive

The Buttons
...........

The order of buttons follows the business flow. For instance, in a sale order,
the logical steps are:

1. Send the quotation
2. Confirm the quotation
3. Create the final invoice
4. Send the goods

Highlighted buttons (in red by default) emphasize the logical next step, to
help the user. It is usually the first active button. On the other hand,
:guilabel:`cancel` buttons *must* remain grey (normal).  For instance, in
Invoice the button :guilabel:`Refund` must never be red.

Technically, buttons are highlighted by adding the class "oe_highlight"::

    <button class="oe_highlight" name="..." type="..." states="..."/>

The Status
..........

Uses the ``statusbar`` widget, and shows the current state in red. States
common to all flows (for instance, a sale order begins as a quotation, then we
send it, then it becomes a full sale order, and finally it is done) should be
visible at all times but exceptions or states depending on particular sub-flow
should only be visible when current.

.. image:: forms/status1.png
   :class: img-responsive

.. image:: forms/status2.png
   :class: img-responsive

The states are shown following the order used in the field (the list in a
selection field, etc). States that are always visible are specified with the
attribute ``statusbar_visible``.

::

    <field name="state" widget="statusbar"
        statusbar_visible="draft,sent,progress,invoiced,done" />

The Sheet
'''''''''

All business views should look like a printed sheet:

.. image:: forms/sheet.png
   :class: img-responsive

1. Elements inside a ``<form>`` or ``<page>`` do not define groups, elements
   inside them are laid out according to normal HTML rules. They content can
   be explicitly grouped using ``<group>`` or regular ``<div>`` elements.
2. By default, the element ``<group>`` defines two columns inside, unless an
   attribute ``col="n"`` is used.  The columns have the same width (1/n th of
   the group's width). Use a ``<group>`` element to produce a column of fields.
3. To give a title to a section, add a ``string`` attribute to a ``<group>`` element::

     <group string="Time-sensitive operations">

   this replaces the former use of ``<separator string="XXX"/>``.
4. The ``<field>`` element does not produce a label, except as direct children
   of a ``<group>`` element\ [#backwards-compatibility]_.  Use :samp:`<label
   for="{field_name}>` to produce a label of a field.

Sheet Headers
.............

Some sheets have headers with one or more fields, and the labels of those
fields are only shown in edit mode.

.. list-table::
   :header-rows: 1

   * - View mode
     - Edit mode
   * - .. image:: forms/header.png
          :class: img-responsive
     - .. image:: forms/header2.png
          :class: img-responsive

Use HTML text, ``<div>``, ``<h1>``, ``<h2>``… to produce nice headers, and
``<label>`` with the class ``oe_edit_only`` to only display the field's label
in edit mode. The class ``oe_inline`` will make fields inline (instead of
blocks): content following the field will be displayed on the same line rather
than on the line below it. The form above is produced by the following XML::

    <label for="name" class="oe_edit_only"/>
    <h1><field name="name"/></h1>

    <label for="planned_revenue" class="oe_edit_only"/>
    <h2>
        <field name="planned_revenue" class="oe_inline"/>
        <field name="company_currency" class="oe_inline oe_edit_only"/> at
        <field name="probability" class="oe_inline"/> % success rate
    </h2>

Button Box
..........

Many relevant actions or links can be displayed in the form. For example, in
Opportunity form, the actions "Schedule a Call" and "Schedule a Meeting" have
an important place in the use of the CRM. Instead of placing them in the
"More" menu, put them directly in the sheet as buttons (on the top) to make
them more visible and more easily accessible.

.. image:: forms/header3.png
   :class: img-responsive

Technically, the buttons are placed inside a ``<div>`` to group them as a
block on the top of the sheet.

::

    <div class="oe_button_box" name="button_box">
        <button string="Schedule/Log Call" name="..." type="action"/>
        <button string="Schedule Meeting" name="action_makeMeeting" type="object"/>
    </div>

Groups and Titles
.................

A column of fields is now produced with a ``<group>`` element, with an
optional title.

.. image:: forms/screenshot-03.png
   :class: img-responsive

::

    <group string="Payment Options">
        <field name="writeoff_amount"/>
        <field name="payment_option"/>
    </group>

It is recommended to have two columns of fields on the form. For this, simply
put the ``<group>`` elements that contain the fields inside a top-level
``<group>`` element.

To make :ref:`view extension <reference/views/inheritance>` simpler, it is
recommended to put a ``name`` attribute on ``<group>`` elements, so new fields
can easily be added at the right place.

Special Case: Subtotals
~~~~~~~~~~~~~~~~~~~~~~~

Some classes are defined to render subtotals like in invoice forms:

.. image:: forms/screenshot-00.png
   :class: img-responsive

::

    <group class="oe_subtotal_footer">
        <field name="amount_untaxed"/>
        <field name="amount_tax"/>
        <field name="amount_total" class="oe_subtotal_footer_separator"/>
        <field name="residual" style="margin-top: 10px"/>
    </group>

Placeholders and Inline Fields
..............................

Sometimes field labels make the form too complex. One can omit field labels,
and instead put a placeholder inside the field. The placeholder text is
visible only when the field is empty. The placeholder should tell what to
place inside the field, it *must not* be an example as they are often confused
with filled data.

One can also group fields together by rendering them "inline" inside an
explicit block element like ``<div>``. This allows grouping semantically
related fields as if they were a single (composite) fields.

The following example, taken from the *Leads* form, shows both placeholders and
inline fields (zip and city).

.. list-table::
   :header-rows: 1

   * - Edit mode
     - View mode
   * - .. image:: forms/placeholder.png
          :class: img-responsive
     - .. image:: forms/screenshot-01.png
          :class: img-responsive

::

    <group>
        <label for="street" string="Address"/>
        <div>
            <field name="street" placeholder="Street..."/>
            <field name="street2"/>
            <div>
                <field name="zip" class="oe_inline" placeholder="ZIP"/>
                <field name="city" class="oe_inline" placeholder="City"/>
            </div>
            <field name="state_id" placeholder="State"/>
            <field name="country_id" placeholder="Country"/>
        </div>
    </group>

Images
......

Images, like avatars, should be displayed on the right of the sheet.  The
product form looks like:

.. image:: forms/screenshot-02.png
   :class: img-responsive

The form above contains a <sheet> element that starts with:

::

    <field name="product_image" widget="image" class="oe_avatar oe_right"/>

Tags
....

Most :class:`~odoo.fields.Many2many` fields, like categories, are better
rendered as a list of tags. Use the widget ``many2many_tags`` for this:

.. image:: forms/screenshot-04.png
   :class: img-responsive

::

    <field name="category_id" widget="many2many_tags"/>

Configuration forms guidelines
------------------------------

Examples of configuration forms: Stages, Leave Type, etc.  This concerns all
menu items under Configuration of each application (like Sales/Configuration).

.. image:: forms/nosheet.png
   :class: img-responsive

1. no header (because no state, no workflow, no button)
2. no sheet

Dialog forms guidelines
-----------------------

Example: "Schedule a Call" from an opportunity.

.. image:: forms/wizard-popup.png
   :class: img-responsive

1. avoid separators (the title is already in the popup title bar, so another
   separator is not relevant)
2. avoid cancel buttons (user generally close the popup window to get the same
   effect)
3. action buttons must be highlighted (red)
4. when there is a text area, use a placeholder instead of a label or a
   separator
5. like in regular form views, put buttons in the <header> element

Configuration Wizards guidelines
--------------------------------

Example: Settings / Configuration / Sales.

1. always in line (no popup)
2. no sheet
3. keep the cancel button (users cannot close the window)
4. the button "Apply" must be red


.. _reference/views/graph:

Graphs
======

The graph view is used to visualize aggregations over a number of records or
record groups. Its root element is ``<graph>`` which can take the following
attributes:

``type``
  one of ``bar`` (default), ``pie`` and ``line``, the type of graph to use
``stacked``
  only used for ``bar`` charts. If present and set to ``True``, stacks bars
  within a group

The only allowed element within a graph view is ``field`` which can have the
following attributes:

``name`` (required)
  the name of a field to use in a graph view. If used for grouping (rather
  than aggregating)

``type``
  indicates whether the field should be used as a grouping criteria or as an
  aggregated value within a group. Possible values are:

  ``row`` (default)
    groups by the specified field. All graph types support at least one level
    of grouping, some may support more. For pivot views, each group gets its
    own row.
  ``col``
    only used by pivot tables, creates column-wise groups
  ``measure``
    field to aggregate within a group

``interval``
  on date and datetime fields, groups by the specified interval (``day``,
  ``week``, ``month``, ``quarter`` or ``year``) instead of grouping on the
  specific datetime (fixed second resolution) or date (fixed day resolution).

.. warning::

   graph view aggregations are performed on database content, non-stored
   function fields can not be used in graph views

Pivots
------

The pivot view is used to visualize aggregations as a `pivot table`_. Its root
element is ``<pivot>`` which can take the following attributes:

``disable_linking``
  Set to ``True`` to remove table cell's links to list view.
``display_quantity``
  Set to ``true`` to display the Quantity column by default.

The elements allowed within a pivot view are the same as for the graph view.

In Pivot view a ``field`` can have a ``widget`` attribute to dictate its format.
The widget should be a field formatter, of which the most interesting are
``date``, ``datetime``, ``float_time``, and ``monetary``.

For instance a timesheet pivot view could be defined as::

    <pivot string="Timesheet">
        <field name="employee_id" type="row"/>
        <field name="date" interval="month" type="col"/>
        <field name="unit_amount" type="measure" widget="float_time"/>
    </pivot>

.. _reference/views/kanban:

Kanban
======

The kanban view is a `kanban board`_ visualisation: it displays records as
"cards", halfway between a :ref:`list view <reference/views/list>` and a
non-editable :ref:`form view <reference/views/form>`. Records may be grouped
in columns for use in workflow visualisation or manipulation (e.g. tasks or
work-progress management), or ungrouped (used simply to visualize records).

The root element of the Kanban view is ``<kanban>``, it can use the following
attributes:

``default_group_by``
  whether the kanban view should be grouped if no grouping is specified via
  the action or the current search. Should be the name of the field to group
  by when no grouping is otherwise specified
``default_order``
  cards sorting order used if the user has not already sorted the records (via
  the list view)
``class``
  adds HTML classes to the root HTML element of the Kanban view
``group_create``
  whether the "Add a new column" bar is visible or not. Default: true.
``group_delete``
  whether groups can be deleted via the context menu. Default: true.
``group_edit``
  whether groups can be edited via the context menu. Default: true.
``quick_create``
  whether it should be possible to create records without switching to the
  form view. By default, ``quick_create`` is enabled when the Kanban view is
  grouped, and disabled when not.

  Set to ``true`` to always enable it, and to ``false`` to always disable it.

Possible children of the view element are:

``field``
  declares fields to use in kanban *logic*. If the field is simply displayed in
  the kanban view, it does not need to be pre-declared.

  Possible attributes are:

  ``name`` (required)
    the name of the field to fetch

``progressbar``
  declares a progressbar element to put on top of kanban columns.

  Possible attributes are:

  ``field`` (required)
    the name of the field whose values are used to subgroup column's records in
    the progressbar

  ``colors`` (required)
    JSON mapping the above field values to either "danger", "warning" or
    "success" colors

  ``sum_field`` (optional)
    the name of the field whose column's records' values will be summed and
    displayed next to the progressbar (if omitted, displays the total number of
    records)

``templates``
  defines a list of :ref:`reference/qweb` templates. Cards definition may be
  split into multiple templates for clarity, but kanban views *must* define at
  least one root template ``kanban-box``, which will be rendered once for each
  record.

  The kanban view uses mostly-standard :ref:`javascript qweb
  <reference/qweb/javascript>` and provides the following context variables:

  ``widget``
    the current :js:class:`KanbanRecord`, can be used to fetch some
    meta-information. These methods are also available directly in the
    template context and don't need to be accessed via ``widget``
  ``record``
    an object with all the requested fields as its attributes. Each field has
    two attributes ``value`` and ``raw_value``, the former is formatted
    according to current user parameters, the latter is the direct value from
    a :meth:`~odoo.models.Model.read` (except for date and datetime fields
    that are `formatted according to user's locale
    <https://github.com/odoo/odoo/blob/a678bd4e/addons/web_kanban/static/src/js/kanban_record.js#L102>`_)
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

If you need to extend the Kanban view, see :js:class::`the JS API <KanbanRecord>`.

.. _reference/views/calendar:

Calendar
========

Calendar views display records as events in a daily, weekly or monthly
calendar. Their root element is ``<calendar>``. Available attributes on the
calendar view are:

``date_start`` (required)
    name of the record's field holding the start date for the event
``date_stop``
    name of the record's field holding the end date for the event, if
    ``date_stop`` is provided records become movable (via drag and drop)
    directly in the calendar
``date_delay``
    alternative to ``date_stop``, provides the duration of the event instead of
    its end date (unit: day)
``color``
    name of a record field to use for *color segmentation*. Records in the
    same color segment are allocated the same highlight color in the calendar,
    colors are allocated semi-randomly.
    Displayed the display_name/avatar of the visible record in the sidebar
``readonly_form_view_id``
    view to open in readonly mode
``form_view_id``
    view to open when the user create or edit an event. Note that if this attribute
    is not set, the calendar view will fall back to the id of the form view in the
    current action, if any.
``event_open_popup``
    If the option 'event_open_popup' is set to true, then the calendar view will
    open events (or records) in a FormViewDialog. Otherwise, it will open events
    in a new form view (with a do_action)
``quick_add``
    enables quick-event creation on click: only asks the user for a ``name``
    and tries to create a new event with just that and the clicked event
    time. Falls back to a full form dialog if the quick creation fails
``all_day``
    name of a boolean field on the record indicating whether the corresponding
    event is flagged as day-long (and duration is irrelevant)
``mode``
    Default display mode when loading the calendar.
    Possible attributes are: ``day``, ``week``, ``month``

``<field>``
  declares fields to aggregate or to use in kanban *logic*. If the field is
  simply displayed in the calendar cards.

  Fields can have additional attributes:

    ``invisible``
        use "True" to hide the value in the cards
    ``avatar_field``
        only for x2many field, to display the avatar instead the display_name
        in the cards
    ``write_model`` and ``write_field``
        you can add a filter and save the result in the defined model, the
        filter is added in the sidebar

``templates``
  defines the :ref:`reference/qweb` template ``calendar-box``. Cards definition
  may be split into multiple templates for clarity which will be rendered once
  for each record.

  The kanban view uses mostly-standard :ref:`javascript qweb
  <reference/qweb/javascript>` and provides the following context variables:

  ``widget``
    the current :js:class:`KanbanRecord`, can be used to fetch some
    meta-information. These methods are also available directly in the
    template context and don't need to be accessed via ``widget``
    ``getColor`` to convert in a color integer
    ``getAvatars`` to convert in an avatar image
    ``displayFields`` list of not invisible fields
  ``record``
    an object with all the requested fields as its attributes. Each field has
    two attributes ``value`` and ``raw_value``
  ``event``
    the calendar event object
  ``format``
    format method to convert values into a readable string with the user
    parameters
  ``fields``
    definition of all model fields
    parameters
  ``user_context``
    self-explanatory
  ``read_only_mode``
    self-explanatory

.. _reference/views/gantt:

Gantt
=====

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
``duration_unit``
  one of ``minute``, ``hour`` (default), ``day``, ``week``, ``month``, ``year``

``default_group_by``
  name of a field to group tasks by
``type``
  ``gantt`` classic gantt view (default)

  ``consolidate`` values of the first children are consolidated in the gantt's task

  ``planning`` children are displayed in the gantt's task
``consolidation``
  field name to display consolidation value in record cell
``consolidation_max``
  dictionary with the "group by" field as key and the maximum consolidation
  value that can be reached before displaying the cell in red
  (e.g. ``{"user_id": 100}``)
``consolidation_exclude``
  name of the field that describe if the task has to be excluded
  from the consolidation
  if set to true it displays a striped zone in the consolidation line

  .. warning::
      The dictionnary definition must use double-quotes, ``{'user_id': 100}`` is
      not a valid value
``string``
  string to display next to the consolidation value, if not specified, the label
  of the consolidation field will be used
``fold_last_level``
  If a value is set, the last grouping level is folded
``round_dnd_dates``
  enables rounding the task's start and end dates to the nearest scale marks
``drag_resize``
  resizing of the tasks, default is ``true``

``progress``
  name of a field providing the completion percentage for the record's event,
  between 0 and 100

.. _reference/views/diagram:

Diagram
=======

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
      :class:`~odoo.fields.Many2one` field of the edge's model pointing to
      the edge's source node record
    ``destination`` (required)
      :class:`~odoo.fields.Many2one` field of the edge's model pointing to
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
======

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
                  if a ``context`` is specified. To only generate context
                  values, set ``filter_domain`` to an empty list:
                  ``filter_domain="[]"``
    ``groups``
        make the field only available to specific users
    ``widget``
        use specific search widget for the field (the only use case in
        standard Odoo 8.0 is a ``selection`` widget for
        :class:`~odoo.fields.Many2one` fields)
    ``domain``
        if the field can provide an auto-completion
        (e.g. :class:`~odoo.fields.Many2one`), filters the possible
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

    .. tip::

       .. versionadded:: 7.0

       Sequences of filters (without non-filters separating them) are treated
       as inclusively composited: they will be composed with ``OR`` rather
       than the usual ``AND``, e.g.

       ::

          <filter domain="[('state', '=', 'draft')]"/>
          <filter domain="[('state', '=', 'done')]"/>

       if both filters are selected, will select the records whose ``state``
       is ``draft`` or ``done``, but

       ::

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
---------------

Search fields and filters can be configured through the action's ``context``
using :samp:`search_default_{name}` keys. For fields, the value should be the
value to set in the field, for filters it's a boolean value. For instance,
assuming ``foo`` is a field and ``bar`` is a filter an action context of:

.. code-block:: python

  {
    'search_default_foo': 'acro',
    'search_default_bar': 1
  }

will automatically enable the ``bar`` filter and search the ``foo`` field for
*acro*.

.. _reference/views/qweb:

QWeb
====

QWeb views are standard :ref:`reference/qweb` templates inside a view's
``arch``. They don't have a specific root element.

A QWeb view can only contain a single template\ [#template_inherit]_, and the
template's name *must* match the view's complete (including module name)
:term:`external id`.

:ref:`reference/data/template` should be used as a shortcut to define QWeb
views.

.. [#backwards-compatibility] for backwards compatibility reasons
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
