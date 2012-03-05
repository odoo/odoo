Creating a new client action
============================

Client actions are the client-side of OpenERP's "Server Actions": instead of
allowing for semi-arbitrary code to be executed in the server, they allow
for execution of client-customized code.

On the server side, a client action is an action of type ``ir.actions.client``,
which has (at most) two properties: a mandatory ``tag``, which is an arbitrary
string by which the client will identify the action, and an optional ``params``
which is simply a map of keys and values sent to the client as-is (this way,
client actions can be made generic and reused in multiple contexts).

General Structure
-----------------

In the OpenERP Web code, a client action only requires two pieces of
information:

* Mapping the action's ``tag`` to an OpenERP Web object

* The OpenERP Web object itself, which must inherit from
  :js:class:`openerp.web.Widget`

Our example will be the actual code for the widgets client action (a client
action displaying a ``res.widget`` object, used in the homepage dashboard of
the web client):

.. code-block:: javascript

    // Registers the object 'openerp.web_dashboard.Widget' to the client
    // action tag 'board.home.widgets'
    openerp.web.client_actions.add(
        'board.home.widgets', 'openerp.web_dashboard.Widget');
    // This object inherits from View, but only Widget is required
    openerp.web_dashboard.Widget = openerp.web.View.extend({
        template: 'HomeWidget'
    });

At this point, the generic ``Widget`` lifecycle takes over, the template is
rendered, inserted in the client DOM, bound on the object's ``$element``
property and the object is started.

If the client action takes parameters, these parameters are passed in as a
second positional parameter to the constructor:

.. code-block:: javascript

    init: function (parent, params) {
        // execute the Widget's init
        this._super(parent);
        // board.home.widgets only takes a single param, the identifier of the
        // res.widget object it should display. Store it for later
        this.widget_id = params.widget_id;
    }

More complex initialization (DOM manipulations, RPC requests, ...) should be
performed in the ``start()`` method.

.. note::
    As required by ``Widget``'s contract, if ``start`` executes any
    asynchronous code it should return a ``$.Deferred`` so callers know when
    it's ready for interaction.

    Although generally speaking client actions are not really interacted with.

.. code-block:: javascript

    start: function () {
        return $.when(
            this._super(),
            // Simply read the res.widget object this action should display
            new openerp.web.DataSet(this, 'res.widget').read_ids(
                [this.widget_id], ['title'], this.on_widget_loaded));
    }

The client action can then behave exactly as it wishes to within its root
(``this.$element``). In this case, it performs further renderings once its
widget's content is retrieved:

.. code-block:: javascript

    on_widget_loaded: function (widgets) {
        var widget = widgets[0];
        var url = _.sprintf(
            '/web_dashboard/widgets/content?session_id=%s&widget_id=%d',
            this.session.session_id, widget.id);
        this.$element.html(QWeb.render('HomeWidget.content', {
            widget: widget,
            url: url
        }));
    }
