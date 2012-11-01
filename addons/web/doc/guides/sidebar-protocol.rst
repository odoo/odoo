Adding a sidebar to a view
==========================

Initialization
--------------

Each view has the responsibility to create its sidebar (or not) if and only if
the ``sidebar`` flag is set in its options.

In that case, it should use the ``sidebar_id`` value (from its options) to
initialize the sidebar at the right position in the DOM:

.. code-block:: javascript

    if (this.options.sidebar && this.options.sidebar_id) {
        this.sidebar = new openerp.web.Sidebar(this, this.options.sidebar_id);
        this.sidebar.start();
    }

Because the sidebar is an old-style widget, it must be started after being
initialized.

Sidebar communication protocol
------------------------------

In order to behave correctly, a sidebar needs informations from its parent
view.

This information is extracted via a very basic protocol consisting of a
property and two methods:

.. js:attribute:: dataset

    the view's dataset, used to fetch the currently active model and provide it
    to remote action handlers as part of the basic context

.. js:function:: get_selected_ids()

    Used to query the parent view for the set of currently available record
    identifiers. Used to setup the basic context's ``active_id`` and
    ``active_ids`` keys.

    .. warning::

        :js:func:`get_selected_ids` must return at least one id

    :returns: an array of at least one id
    :rtype: Array<Number>

.. js:function:: sidebar_context()

    Queries the view for additional context data to provide to the sidebar.

    :js:class:`~openerp.base.View` provides a default NOOP implementation,
    which simply resolves to an empty object.

    :returns: a promise yielding an object on success, this object is mergeed
              into the sidebar's own context
    :rtype: $.Deferred<Object>

Programmatic folding and unfolding
----------------------------------

The sidebar object starts folded. It provides three methods to handle its
folding status:

.. js:function:: do_toggle

    Toggles the status of the sidebar

.. js:function:: do_fold

    Forces the sidebar closed if it's currently open

.. js:function:: do_unfold

    Forces the sidebar open if it's currently closed

