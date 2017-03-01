:banner: banners/actions.jpg

.. _reference/actions:

=======
Actions
=======

Actions define the behavior of the system in response to user actions: login,
action button, selection of an invoice, ...

Actions can be stored in the database or returned directly as dictionaries in
e.g. button methods. All actions share two mandatory attributes:

``type``
    the category of the current action, determines which fields may be
    used and how the action is interpreted
``name``
    short user-readable description of the action, may be displayed in the
    client's interface

A client can get actions in 4 forms:

``False``
    if any action dialog is currently open, close it
A string
    if a :ref:`client action <reference/actions/client>` matches, interpret as
    a client action's tag, otherwise treat as a number
A number
    read the corresponding action record from the database, may be a database
    identifier or an :term:`external id`
A dictionary
    treat as a client action descriptor and execute

.. _reference/actions/window:

Window Actions (``ir.actions.act_window``)
==========================================

The most common action type, used to present visualisations of a model through
:ref:`views <reference/views>`: a window action defines a set of view types
(and possibly specific views) for a model (and possibly specific record of the
model).

Its fields are:

``res_model``
    model to present views for
``views``
    a list of ``(view_id, view_type)`` pairs. The second element of each pair
    is the category of the view (tree, form, graph, ...) and the first is
    an optional database id (or ``False``). If no id is provided, the client
    should fetch the default view of the specified type for the requested
    model (this is automatically done by
    :meth:`~odoo.models.Model.fields_view_get`). The first type of the
    list is the default view type and will be open by default when the action
    is executed. Each view type should be present at most once in the list
``res_id`` (optional)
    if the default view is ``form``, specifies the record to load (otherwise
    a new record should be created)
``search_view_id`` (optional)
    ``(id, name)`` pair, ``id`` is the database identifier of a specific
    search view to load for the action. Defaults to fetching the default
    search view for the model
``target`` (optional)
    whether the views should be open in the main content area (``current``),
    in full screen mode (``fullscreen``) or in a dialog/popup (``new``). Use
    ``main`` instead of ``current`` to clear the breadcrumbs. Defaults to
    ``current``.
``context`` (optional)
    additional context data to pass to the views
``domain`` (optional)
    filtering domain to implicitly add to all view search queries
``limit`` (optional)
    number of records to display in lists by default. Defaults to 80 in the
    web client
``auto_search`` (optional)
    whether a search should be performed immediately after loading the default
    view. Defaults to ``True``

For instance, to open customers (partner with the ``customer`` flag set) with
list and form views::

    {
        "type": "ir.actions.act_window",
        "res_model": "res.partner",
        "views": [[False, "tree"], [False, "form"]],
        "domain": [["customer", "=", true]],
    }

Or to open the form view of a specific product (obtained separately) in a new
dialog::

    {
        "type": "ir.actions.act_window",
        "res_model": "product.product",
        "views": [[False, "form"]],
        "res_id": a_product_id,
        "target": "new",
    }

In-database window actions have a few different fields which should be ignored
by clients, mostly to use in composing the ``views`` list:

``view_mode``
    comma-separated list of view types as a string. All of these types will be
    present in the generated ``views`` list (with at least a ``False`` view_id)
``view_ids``
    M2M\ [#notquitem2m]_ to view objects, defines the initial content of
    ``views``
``view_id``
    specific view added to the ``views`` list in case its type is part of the
    ``view_mode`` list and not already filled by one of the views in
    ``view_ids``

These are mostly used when defining actions from :ref:`reference/data`:

.. code-block:: xml

    <record model="ir.actions.act_window" id="test_action">
        <field name="name">A Test Action</field>
        <field name="res_model">some.model</field>
        <field name="view_mode">graph</field>
        <field name="view_id" ref="my_specific_view"/>
    </record>

will use the "my_specific_view" view even if that's not the default view for
the model.

The server-side composition of the ``views`` sequence is the following:

* get each ``(id, type)`` from ``view_ids`` (ordered by ``sequence``)
* if ``view_id`` is defined and its type isn't already filled, append its
  ``(id, type)``
* for each unfilled type in ``view_mode``, append ``(False, type)``

.. todo::

    * ``src_model``, ``multi`` seem linked to "sidebar" actions?
    * ``auto_refresh`` looks ignored/deprecated
    * ``usage``?
    * ``groups_id``?
    * ``filter``?

.. _reference/actions/url:

URL Actions (``ir.actions.act_url``)
====================================

Allow opening a URL (website/web page) via an Odoo action. Can be customized
via two fields:

``url``
    the address to open when activating the action
``target``
    opens the address in a new window/page if ``new``, replaces
    the current content with the page if ``self``. Defaults to ``new``

::

    {
        "type": "ir.actions.act_url",
        "url": "http://odoo.com",
        "target": "self",
    }

will replace the current content section by the Odoo home page.

.. _reference/actions/server:

Server Actions (``ir.actions.server``)
======================================

Allow triggering complex server code from any valid action location. Only
two fields are relevant to clients:

``id``
    the in-database identifier of the server action to run
``context`` (optional)
    context data to use when running the server action

In-database records are significantly richer and can perform a number of
specific or generic actions based on their ``state``. Some fields (and
corresponding behaviors) are shared between states:

``model_id``
    Odoo model linked to the action, made available in
    :ref:`evaluation contexts <reference/actions/server/context>`
``condition`` (optional)
    evaluated as Python code using the server action's
    :ref:`evaluation context <reference/actions/server/context>`. If
    ``False``, prevents the action from running. Default: ``True``

Valid action types (``state`` field) are extensible, the default types are:

``code``
--------

The default and most flexible server action type, executes arbitrary Python
code with the action's :ref:`evaluation context
<reference/actions/server/context>`. Only uses one specific type-specific
field:

``code``
    a piece of Python code to execute when the action is called

.. code-block:: xml

    <record model="ir.actions.server" id="print_instance">
        <field name="name">Res Partner Server Action</field>
        <field name="model_id" ref="model_res_partner"/>
        <field name="code">
            raise Warning(object.name)
        </field>
    </record>

.. note::

    The code segment can define a variable called ``action``, which will be
    returned to the client as the next action to execute:

    .. code-block:: xml

        <record model="ir.actions.server" id="print_instance">
            <field name="name">Res Partner Server Action</field>
            <field name="model_id" ref="model_res_partner"/>
            <field name="code">
                if object.some_condition():
                    action = {
                        "type": "ir.actions.act_window",
                        "view_mode": "form",
                        "res_model": object._name,
                        "res_id": object.id,
                    }
            </field>
        </record>

    will ask the client to open a form for the record if it fulfills some
    condition

This tends to be the only action type created from :ref:`data files
<reference/data>`, other types aside from
:ref:`reference/actions/server/multi` are simpler than Python code to define
from the UI, but not from :ref:`data files <reference/data>`.

.. _reference/actions/server/object_create:

``object_create``
-----------------

Creates a new record, from scratch (via :meth:`~odoo.models.Model.create`)
or by copying an existing record (via :meth:`~odoo.models.Model.copy`)

``use_create``
    the creation policy, one of:

    ``new``
        creates a record in the model specified by ``model_id``
    ``new_other``
        creates a record in the model specified by ``crud_model_id``
    ``copy_current``
        copies the record on which the action was invoked
    ``copy_other``
        copies an other record, obtained via ``ref_object``
``fields_lines``
    fields to override when creating or copying the record.
    :class:`~odoo.fields.One2many` with the fields:

    ``col1``
        ``ir.model.fields`` to set in the model implied by ``use_create``
    ``value``
        value for the field, interpreted via ``type``
    ``type``
        If ``value``, the ``value`` field is interpreted as a literal value
        (possibly converted), if ``equation`` the ``value`` field is
        interpreted as a Python expression and evaluated
``crud_model_id``
    model in which to create a new record, if ``use_create`` is set to
    ``new_other``
``ref_object``
    :class:`~odoo.fields.Reference` to an arbitrary record to copy, used if
    ``use_create`` is set to ``copy_other``
``link_new_record``
    boolean flag linking the newly created record to the current one via a
    many2one field specified through ``link_field_id``, defaults to ``False``
``link_field_id``
    many2one to ``ir.model.fields``, specifies the current record's m2o field
    on which the newly created record should be set (models should match)

``object_write``
----------------

Similar to :ref:`reference/actions/server/object_create` but alters an
existing records instead of creating one

``use_write``
    write policy, one of:

    ``current``
        write to the current record
    ``other``
        write to an other record selected via ``crud_model_id`` and
        ``ref_object``
    ``expression``
        write to an other record whose model is selected via ``crud_model_id``
        and whose id is selected by evaluating ``write_expression``
``write_expression``
    Python expression returning a record or an object id, used when
    ``use_write`` is set to ``expression`` in order to decide which record
    should be modified
``fields_lines``
    see :ref:`reference/actions/server/object_create`
``crud_model_id``
    see :ref:`reference/actions/server/object_create`
``ref_object``
    see :ref:`reference/actions/server/object_create`

.. _reference/actions/server/multi:

``multi``
---------

Executes multiple actions one after the other. Actions to execute are defined
via the ``child_ids`` m2m. If sub-actions themselves return actions, the last
one will be returned to the client as the multi's own next action

``client_action``
-----------------

Indirection for directly returning an other action defined using
``action_id``. Simply returns that action to the client for execution.

.. _reference/actions/server/context:

Evaluation context
------------------

A number of keys are available in the evaluation context of or surrounding
server actions:

``model``
    the model object linked to the action via ``model_id``
``object``, ``obj``
    only available if ``active_model`` and ``active_id`` are provided (via
    context) otherwise ``None``. The actual record selected by ``active_id``
``pool``
    the current database registry
``datetime``, ``dateutil``, ``time``
    corresponding Python modules
``cr``
    the current cursor
``user``
    the current user record
``context``
    execution context
``Warning``
    constructor for the ``Warning`` exception

.. _reference/actions/report:

Report Actions (``ir.actions.report.xml``)
==========================================

Triggers the printing of a report

``name`` (mandatory)
    only useful as a mnemonic/description of the report when looking for one
    in a list of some sort
``model`` (mandatory)
    the model your report will be about
``report_type`` (mandatory)
    either ``qweb-pdf`` for PDF reports or ``qweb-html`` for HTML
``report_name``
    the name of your report (which will be the name of the PDF output)
``groups_id``
    :class:`~odoo.fields.Many2many` field to the groups allowed to view/use
    the current report
``paperformat_id``
    :class:`~odoo.fields.Many2one` field to the paper format you wish to
    use for this report (if not specified, the company format will be used)
``attachment_use``
    if set to ``True``, the report is only generated once the first time it is
    requested, and re-printed from the stored report afterwards instead of
    being re-generated every time.

    Can be used for reports which must only be generated once (e.g. for legal
    reasons)
``attachment``
    python expression that defines the name of the report; the record is
    accessible as the variable ``object``

.. _reference/actions/client:

Client Actions (``ir.actions.client``)
======================================

Triggers an action implemented entirely in the client.

``tag``
    the client-side identifier of the action, an arbitrary string which
    the client should know how to react to
``params`` (optional)
    a Python dictionary of additional data to send to the client, alongside
    the client action tag
``target`` (optional)
    whether the client action should be open in the main content area
    (``current``), in full screen mode (``fullscreen``) or in a dialog/popup
    (``new``). Use ``main`` instead of ``current`` to clear the breadcrumbs.
    Defaults to ``current``.

::

    {
        "type": "ir.actions.client",
        "tag": "pos.ui"
    }

tells the client to start the Point of Sale interface, the server has no idea
how the POS interface works.

.. [#notquitem2m] technically not an M2M: adds a sequence field and may be
                  composed of just a view type, without a view id.
