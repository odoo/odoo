:banner: banners/javascript.jpg

=====================
Javascript Cheatsheet
=====================

There are many ways to solve a problem in JavaScript, and in Odoo.  However, the
Odoo framework was designed to be extensible (this is a pretty big constraint),
and some common problems have a nice standard solution.  The standard solution
has probably the advantage of being easy to understand for an odoo developers,
and will probably keep working when Odoo is modified.

This document tries to explain the way one could solve some of these issues.
Note that this is not a reference.  This is just a random collection of recipes,
or explanations on how to proceed in some cases.


First of all, remember that the first rule of customizing odoo with JS is:
*try to do it in python*.  This may seem strange, but the python framework is
quite extensible, and many behaviours can be done simply with a touch of xml or
python.  This has usually a lower cost of maintenance than working with JS:

- the JS framework tends to change more, so JS code needs to be more frequently
  updated
- it is often more difficult to implement a customized behaviour if it needs to
  communicate with the server and properly integrate with the javascript framework.
  There are many small details taken care by the framework that customized code
  needs to replicate.  For example, responsiveness, or updating the url, or
  displaying data without flickering.


.. note:: This document does not really explain any concepts. This is more a
            cookbook.  For more details, please consult the javascript reference
            page (see :doc:`javascript_reference`)

Creating a new field widget
===========================

This is probably a really common usecase: we want to display some information in
a form view in a really specific (maybe business dependent) way.  For example,
assume that we want to change the text color depending on some business condition.

This can be done in three steps: creating a new widget, registering it in the
field registry, then adding the widget to the field in the form view

- creating a new widget:
    This can be done by extending a widget:

    .. code-block:: javascript

        var FieldChar = require('web.basic_fields').FieldChar;

        var CustomFieldChar = Fieldchar.extend({
            renderReadonly: function () {
                // implement some custom logic here
            },
        });

- registering it in the field registry:
    The web client needs to know the mapping between a widget name and its
    actual class.  This is done by a registry:

    .. code-block:: javascript

        var fieldRegistry = require('web.field_registry');

        fieldRegistry.add('my-custom-field', CustomFieldChar);

- adding the widget in the form view
    .. code-block:: xml

        <field name="somefield" widget="my-custom-field"/>

    Note that only the form, list and kanban views use this field widgets registry.
    These views are tightly integrated, because the list and kanban views can
    appear inside a form view).

Modifying an existing field widget
==================================

Another use case is that we want to modify an existing field widget.  For
example, the voip addon in odoo need to modify the FieldPhone widget to add the
possibility to easily call the given number on voip. This is done by *including*
the FieldPhone widget, so there is no need to change any existing form view.

Field Widgets (instances of (subclass of) AbstractField) are like every other
widgets, so they can be monkey patched. This looks like this:

.. code-block:: javascript

    var basic_fields = require('web.basic_fields');
    var Phone = basic_fields.FieldPhone;

    Phone.include({
        events: _.extend({}, Phone.prototype.events, {
            'click': '_onClick',
        }),

        _onClick: function (e) {
            if (this.mode === 'readonly') {
                e.preventDefault();
                var phoneNumber = this.value;
                // call the number on voip...
            }
        },
    });

Note that there is no need to add the widget to the registry, since it is already
registered.

Modifying a main widget from the interface
==========================================

Another common usecase is the need to customize some elements from the user
interface.  For example, adding a message in the home menu.  The usual process
in this case is again to *include* the widget.  This is the only way to do it,
since there are no registries for those widgets.

This is usually done with code looking like this:

.. code-block:: javascript

    var AppSwitcher = require('web_enterprise.AppSwitcher');

    AppSwitcher.include({
        render: function () {
            this._super();
            // do something else here...
        },
    });


Adding a client action
======================

A client action is a widget which will control the part of the screen below the
menu bar.  It can have a control panel, if necessary.  Defining a client action
can be done in two steps: implementing a new widget, and registering the widget
in the action registry.

- Implementing a new client action:
    This is done by creating a widget:

    .. code-block:: javascript

        var ControlPanelMixin = require('web.ControlPanelMixin');
        var Widget = require('web.Widget');

        var ClientAction = Widget.extend(ControlPanelMixin, {
            ...
        });

    Do not add the controlpanel mixin if you do not need it.  Note that some
    code is needed to interact with the control panel (via the
    ``update_control_panel`` method given by the mixin).

- Registering the client action:
    As usual, we need to make the web client aware of the mapping between
    client actions and the actual class:

    .. code-block:: javascript

        var core = require('web.core');

        core.action_registry.add('my-custom-action', ClientAction);


    Then, to use the client action in the web client, we need to create a client
    action record (a record of the model ``ir.actions.client``) with the proper
    ``tag`` attribute:

    .. code-block:: xml

        <record id="my_client_action" model="ir.actions.client">
            <field name="name">Some Name</field>
            <field name="tag">my-custom-action</field>
        </record>

Creating a new view (from scratch)
==================================

Creating a new view is a more advanced topic.  This cheatsheet will only
highlight the steps that will probably need to be done (in no particular order):

- adding a new view type to the field ``type`` of ``ir.ui.view``::

    class View(models.Model):
        _inherit = 'ir.ui.view'

        type = fields.Selection(selection_add=[('map', "Map")])

- adding the new view type to the field ``view_mode`` of ``ir.actions.act_window.view``::

    class ActWindowView(models.Model):
        _inherit = 'ir.actions.act_window.view'

        view_mode = fields.Selection(selection_add=[('map', "Map")])


- creating the four main pieces which makes a view (in JavaScript):
    we need a view (a subclass of ``AbstractView``, this is the factory), a
    renderer (from ``AbstractRenderer``), a controller (from ``AbstractController``)
    and a model (from ``AbstractModel``).  I suggest starting by simply
    extending the superclasses:

    .. code-block:: javascript

        var AbstractController = require('web.AbstractController');
        var AbstractModel = require('web.AbstractModel');
        var AbstractRenderer = require('web.AbstractRenderer');
        var AbstractView = require('web.AbstractView');

        var MapController = AbstractController.extend({});
        var MapRenderer = AbstractRenderer.extend({});
        var MapModel = AbstractModel.extend({});

        var MapView = AbstractView.extend({
            config: {
                Model: MapModel,
                Controller: MapController,
                Renderer: MapRenderer,
            },
        });

- adding the view to the registry:
    As usual, the mapping between a view type and the actual class needs to be
    updated:

    .. code-block:: javascript

        var viewRegistry = require('web.view_registry');

        viewRegistry.add('map', MapView);

- implementing the four main classes:
    The ``View`` class needs to parse the ``arch`` field and setup the other
    three classes.  The ``Renderer`` is in charge of representing the data in
    the user interface, the ``Model`` is supposed to talk to the server, to
    load data and process it.  And the ``Controller`` is there to coordinate,
    to talk to the web client, ...

- creating some views in the database:
    .. code-block:: xml

        <record id="customer_map_view" model="ir.ui.view">
            <field name="name">customer.map.view</field>
            <field name="model">res.partner</field>
            <field name="arch" type="xml">
                <map latitude="partner_latitude" longitude="partner_longitude">
                    <field name="name"/>
                </map>
            </field>
        </record>


Customizing an existing view
============================

Assume we need to create a custom version of a generic view.  For example, a
kanban view with some extra *ribbon-like* widget on top (to display some
specific custom information). In that case, this can be done with 3 steps:
extend the kanban view (which also probably mean extending controllers/renderers
and/or models), then registering the view in the view registry, and finally,
using the view in the kanban arch (a specific example is the helpdesk dashboard).

- extending a view:
    Here is what it could look like:

    .. code-block:: javascript

        var HelpdeskDashboardRenderer = KanbanRenderer.extend({
            ...
        });

        var HelpdeskDashboardModel = KanbanModel.extend({
            ...
        });

        var HelpdeskDashboardController = KanbanController.extend({
            ...
        });

        var HelpdeskDashboardView = KanbanView.extend({
            config: _.extend({}, KanbanView.prototype.config, {
                Model: HelpdeskDashboardModel,
                Renderer: HelpdeskDashboardRenderer,
                Controller: HelpdeskDashboardController,
            }),
        });

- adding it to the view registry:
    as usual, we need to inform the web client of the mapping between the name
    of the views and the actual class.

    .. code-block:: javascript

        var viewRegistry = require('web.view_registry');
        viewRegistry.add('helpdesk_dashboard', HelpdeskDashboardView);

- using it in an actual view:
    we now need to inform the web client that a specific ``ir.ui.view`` needs to
    use our new class.  Note that this is a web client specific concern.  From
    the point of view of the server, we still have a kanban view.  The proper
    way to do this is by using a special attribute ``js_class`` (which will be
    renamed someday into ``widget``, because this is really not a good name) on
    the root node of the arch:

    .. code-block:: xml

        <record id="helpdesk_team_view_kanban" model="ir.ui.view" >
            ...
            <field name="arch" type="xml">
                <kanban js_class="helpdesk_dashboard">
                    ...
                </kanban>
            </field>
        </record>

.. note::

    Note: you can change the way the view interprets the arch structure.  However,
    from the server point of view, this is still a view of the same base type,
    subjected to the same rules (rng validation, for example).  So, your views still
    need to have a valid arch field.