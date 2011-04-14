OpenERP Web Core and standard addons
====================================

* General organization and core ideas (design philosophies)
* Internal documentation, autodoc, Python and JS domains
* QWeb code documentation/description
* Documentation of the OpenERP APIs and choices taken based on that?
* Style guide and coding conventions (PEP8? More)
* Test frameworks in JS?

Standard Views
--------------

Search View
+++++++++++

The OpenERP search view really is a sub-view, used in support of views
acting on collections of records (list view or graph view, for
instance).

Its main goal is to collect information from its widgets (themselves
collecting information from the users) and make those available to the
rest of the client.

The search view's root is :js:class:`~openerp.base.SearchView`. This
object should never need to be created or managed directly, its
lifecycle should be driven by the
:js:class:`~openerp.base.ViewManager`.

.. TODO: insert SearchView constructor here

The search view defines a number of internal and external protocols to
communicate with the objects around and within it. Most of these
protocols are informal, and types available for inheritance are more
mixins than mandatory.

Events
""""""

``on_loaded``

  .. TODO: method openerp.base.SearchView.on_loaded

  Fires when the search view receives its view data (the result of
  ``fields_view_get``). Hooking up before the event allows for
  altering view data before it can be used.

  By the time ``on_loaded`` is done, the search view is guaranteed to
  be fully set up and ready to use.

``on_search``

  .. TODO: method openerp.base.SearchView.on_search

  Event triggered after a user asked for a search. The search view
  fires this event after collecting all input data (contexts, domains
  and group_by contexts). Note that the search view does *not* merge
  those (or otherwise evaluate them), they are returned as provided by
  the various inputs within the view.

``on_clear``

  .. TODO: method openerp.base.SearchView.on_clear

  Triggered after a user asked for a form clearing.

Input management
""""""""""""""""

An important concept in the search view is that of input. It is both
an informal protocol and an abstract type that can be inherited from.

Inputs are widgets which can contain user data (a char widget for
instance, or a selection box). They are capable of action and of
reaction:

.. _views-search-registration:

``registration``

  This is an input action. Inputs have to register themselves to the
  main view (which they receive as a constructor argument). This is
  performed by pushing themselves on the
  :js:attr:`openerp.base.SearchView.inputs` array.

``get_context``

  An input reaction. When it needs to collect contexts, the view calls
  ``get_context()`` on all its inputs.

  Inputs can react in the following manners:

  * Return a context (an object), this is the "normal" response if the
    input holds a value.

  * Return a value that evaluates as false (generally ``null``). This
    value indicates the input does not contain any value and will not
    affect the results of the search.

  * Raise :js:class:`openerp.base.search.Invalid` to indicate that it
    holds a value but this value can not be used in the search
    (because it is incorrectly formatted or nonsensical). Raising
    :js:class:`~openerp.base.search.Invalid` is guaranteed to cancel
    the search process.

    :js:class:`~openerp.base.search.Invalid` takes three mandatory
    arguments: an identifier (a name for instance), the invalid value,
    and a validation message indicating the issue.

``get_domain``

  The second input reaction, the possible behaviors of inputs are the
  same as for ``get_context``.

The :js:class:`openerp.base.search.Input` type implements registration
on its own, but its implementations of ``get_context`` and
``get_domain`` simply raise errors and *must* be overridden.

One last action is for filters, as an activation order has to be kept
on them for some controls (to establish the correct grouping sequence,
for instance).

To that end, filters can call
:js:func:`openerp.base.Search.do_toggle_filter`, providing themselves
as first argument.

Filters calling :js:func:`~openerp.base.Search.do_toggle_filter` also
need to implement a method called
:js:func:`~openerp.base.search.Filter.is_enabled`, which the search
view will use to know the current status of the filter.

The search view automatically triggers a search after calls to
:js:func:`~openerp.base.Search.do_toggle_filter`.

Life cycle
""""""""""

The search view has a pretty simple and linear life cycle, in three main steps:

:js:class:`~openerp.base.SearchView.init`

  Nothing interesting happens here

:js:func:`~openerp.base.SearchView.start`

  Called by the main view's creator, this is the main initialization
  step for the list view.

  It begins with a remote call to fetch the view's descriptors
  (``fields_view_get``).

  Once the remote call is complete, the ``on_loaded`` even happens,
  holding three main operations:

  :js:func:`~openerp.base.SearchView.make_widgets`

    Builds and returns the top-level widgets of the search
    view. Because it returns an array of widget lines (a 2-dimensional
    matrix of widgets) it should be called recursively by container
    widgets (:js:class:`openerp.base.search.Group` for instance).

  :js:func:`~openerp.base.search.Widget.render`

    Called by the search view on all top-level widgets. Container
    widgets should recursively call this method on their own children
    widgets.

    Widgets are provided with a mapping of ``{name: value}`` holding
    default values for the search view. They can freely pick their
    initial values from there, but must pass the mapping to their
    children widgets if they have any.

  :js:func:`~openerp.base.search.Widget.start`

    The last operation of the search view startup is to initialize all
    its widgets in order. This is again done recursively (the search
    view starts its children, which have to start their own children).

:js:func:`~openerp.base.SearchView.stop`

  Used before discarding a search view, allows the search view to
  disable its events and pass the message to its own widgets,
  gracefully shutting down the whole view.

Widgets
"""""""

In a search view, the widget is simply a unit of display.

All widgets must be able to react to three events, which will be
called in this order:

:js:func:`~openerp.base.search.Widget.render`

  Called with a map of default values. The widget must return a
  ``String``, which is its HTML representation. That string can be
  empty (if the widget should not be represented).

  Widgets are responsible for asking their children for rendering, and
  for passing along the default values.

:js:func:`~openerp.base.search.Widget.start`

  Called without arguments. At this point, the widget has been fully
  rendered and can set its events up, if any.

  The widget is responsible for starting its children, if it has any.

:js:func:`~openerp.base.search.Widget.stop`

  Gives the widget the opportunity to unbind its events, remove itself
  from the DOM and perform any other cleanup task it may have.

  Event if the widget does not do anything itself, it is responsible
  for shutting down its children.

An abstract type is available and can be inherited from, to simplify
the implementation of those tasks:

.. TODO: insert Widget here

.. remember to document all methods

Inputs
""""""

The search namespace (``openerp.base.search``) provides two more
abstract types, used to implement input widgets:

* :js:class:`openerp.base.search.Input` is the most basic input type,
  it only implements :ref:`input registration
  <views-search-registration>`.

  If inherited from, descendant classes should not call its
  implementations of :js:func:`~openerp.base.search.Input.get_context`
  and :js:func:`~openerp.base.search.Input.get_domain`.

* :js:class:`openerp.base.search.Field` is used to implement more
  "field" widgets (which allow the user to input potentially complex
  values).

  It provides various services for its subclasses:

  * Sets up the field attributes, using attributes from the field and
    the view node.

  * It fills the widget with :js:class:`~openerp.base.search.Filter`
    if the field has any child filter.

  * It automatically generates an identifier based on the field type
    and the field name, using
    :js:func:`~openerp.base.search.Widget.make_id`.

  * It sets up a basic (overridable)
    :js:attr:`~opererp.base.search.Field.template` attribute, combined
    with the previous tasks, this makes subclasses of
    :js:class:`~openerp.base.search.Field` render themselves "for
    free".

  * It provides basic implementations of ``get_context`` and
    ``get_domain``, both hinging on the subclasses implementing
    ``get_value()`` (which should return a correct, converted
    Javascript value):

    :js:func:`~openerp.base.search.Field.get_context`

        Checks if the field has a non-``null`` and non-empty
        (``String``) value, and that the field has a ``context`` attr.

        If both conditions are fullfilled, returns the context.

    :js:func:`~openerp.base.search.Field.get_domain`

        Only requires that the field has a non-``null`` and non-empty
        value.

        If the field has a ``filter_domain``, returns it
        immediately. Otherwise, builds a context using the field's
        name, the field :js:attr:`~openerp.base.search.Field.operator`
        and the field value, and returns it.

.. TODO: insert Input, Field, Filter, and just about every Field subclass

Internal API Doc
----------------

Python
++++++

These classes should be moved to other sections of the doc as needed,
probably.

.. automodule:: openerpweb.openerpweb
    :members: JsonRequest

    See also: :class:`~openerpweb.openerpweb.OpenERPSession`,
    :class:`~openerpweb.openerpweb.OpenERPModel`

.. automodule:: base.controllers.main
    :members:
    :undoc-members:

Testing
-------

Python
++++++

Testing for the OpenERP Web core is similar to :ref:`testing addons
<addons-testing>`: the tests live in ``openerpweb.tests``, unittest2_
is the testing framework and tests can be run via either unittest2
(``unit2 discover``) or via nose_ (``nosetests``).

Tests for the OpenERP Web core can also be run using ``setup.py
test``.


.. _unittest2:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml

.. _nose:
    http://somethingaboutorange.com/mrl/projects/nose/1.0.0/
