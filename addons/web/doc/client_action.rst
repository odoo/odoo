.. highlight:: javascript

Client actions
==============

Client actions are the client-side version of OpenERP's "Server
Actions": instead of allowing for semi-arbitrary code to be executed
in the server, they allow for execution of client-customized code.

On the server side, a client action is an action of type
``ir.actions.client``, which has (at most) two properties: a mandatory
``tag``, which is an arbitrary string by which the client will
identify the action, and an optional ``params`` which is simply a map
of keys and values sent to the client as-is (this way, client actions
can be made generic and reused in multiple contexts).

General Structure
-----------------

In the OpenERP Web code, a client action only requires two pieces of
information:

* Mapping the action's ``tag`` to an object

* Providing said object. Two different types of objects can be mapped
  to a client action:

  * An OpenERP Web widget, which must inherit from
    :js:class:`openerp.web.Widget`

  * A regular javascript function

The major difference is in the lifecycle of these:

* if the client action maps to a function, the function will be called
  when executing the action. The function can have no further
  interaction with the Web Client itself, although it can return an
  action which will be executed after it.

  The function takes 2 parameters: the ActionManager calling it and
  the descriptor for the current action (the ``ir.actions.client``
  dictionary).

* if, on the other hand, the client action maps to a
  :js:class:`~openerp.web.Widget`, that
  :js:class:`~openerp.web.Widget` will be instantiated and added to
  the web client's canvas, with the usual
  :js:class:`~openerp.web.Widget` lifecycle (essentially, it will
  either take over the content area of the client or it will be
  integrated within a dialog).

For example, to create a client action displaying a ``res.widget``
object::

    // Registers the object 'openerp.web_dashboard.Widget' to the client
    // action tag 'board.home.widgets'
    instance.web.client_actions.add(
        'board.home.widgets', 'instance.web_dashboard.Widget');
    instance.web_dashboard.Widget = instance.web.Widget.extend({
        template: 'HomeWidget'
    });

At this point, the generic :js:class:`~openerp.web.Widget` lifecycle
takes over, the template is rendered, inserted in the client DOM,
bound on the object's ``$el`` property and the object is started.

The second parameter to the constructor is the descriptor for the
action itself, which contains any parameter provided::

    init: function (parent, action) {
        // execute the Widget's init
        this._super(parent);
        // board.home.widgets only takes a single param, the identifier of the
        // res.widget object it should display. Store it for later
        this.widget_id = action.params.widget_id;
    }

More complex initialization (DOM manipulations, RPC requests, ...)
should be performed in the :js:func:`~openerp.web.Widget.start()`
method.

.. note::

    As required by :js:class:`~openerp.web.Widget`'s contract, if
    :js:func:`~openerp.web.Widget.start()` executes any asynchronous
    code it should return a ``$.Deferred`` so callers know when it's
    ready for interaction.

.. code-block:: javascript

    start: function () {
        return $.when(
            this._super(),
            // Simply read the res.widget object this action should display
            new instance.web.Model('res.widget').call(
                'read', [[this.widget_id], ['title']])
                    .then(this.proxy('on_widget_loaded'));
    }

The client action can then behave exactly as it wishes to within its
root (``this.$el``). In this case, it performs further renderings once
its widget's content is retrieved::

    on_widget_loaded: function (widgets) {
        var widget = widgets[0];
        var url = _.sprintf(
            '/web_dashboard/widgets/content?session_id=%s&widget_id=%d',
            this.session.session_id, widget.id);
        this.$el.html(QWeb.render('HomeWidget.content', {
            widget: widget,
            url: url
        }));
    }
