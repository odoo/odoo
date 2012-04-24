Search View
===========

OpenERP Web 6.2 implements a unified facets-based search view instead
of the previous form-like search view (composed of buttons and
multiple fields). The goal for this change is twofold:

* Avoid the common issue of users confusing the search view with a
  form view and trying to create their records through it (or entering
  all their data, hitting the ``Create`` button expecting their record
  to be created and losing everything).

* Improve the looks and behaviors of the view, and the fit within
  OpenERP Web's new design.

The internal structure of the faceted search is inspired by
`VisualSearch <http://documentcloud.github.com/visualsearch/>`_ [#]_.

As does VisualSearch, the new search view is based on `Backbone
<http://documentcloud.github.com/backbone/>`_ and makes significant
use of Backbone's models and collections (OpenERP Web's widgets make a
good replacement for Backbone's own views). As a result, understanding
the implementation details of the OpenERP Web 7 search view also
requires a basic understanding of Backbone's models, collections and
events.

.. note::

    This document may mention *fetching* data. This is a shortcut for
    "returning a :js:class:`Deferred` to [whatever is being
    fetched]". Unless further noted, the function or method may opt to
    return nothing by fetching ``null`` (which can easily be done by
    returning ``$.when(null)``, which simply wraps the ``null`` in a
    Deferred).

Working with the search view: creating new inputs
-------------------------------------------------

The primary component of search views, as with all other OpenERP
views, are inputs. The search view has two types of inputs — filters
and fields — but only one is easly customizable: fields.

The mapping from OpenERP field types (and widgets) to search view
objects is stored in the ``openerp.web.search.fields``
:js:class:`~openerp.web.Registry` where new field types and widgets
can be added.

Search view inputs have three main roles:

Loading defaults
++++++++++++++++

Once the search view has initialized all its inputs, it will call
:js:func:`~openerp.web.search.Input.facet_for_defaults` on each input,
passing it a mapping (a javascript object) of ``name:value`` extracted
from the action's context.

This method should fetch a :js:class:`~openerp.web.search.Facet` (or
an equivalent object) for the field's default value if applicable (if
a default value for the field is found in the ``defaults`` mapping).

A default implementation is provided which checks if ``defaults``
contains a non-falsy value for the field's ``@name`` and calls
:js:func:`openerp.web.search.Input.facet_for` with that value.

There is no default implementation of
:js:func:`openerp.web.search.Input.facet_for` [#]_, but
:js:class:`openerp.web.search.Field` provides one, which uses the
value as-is to fetch a :js:class:`~openerp.web.search.Facet`.

Providing completions
+++++++++++++++++++++

An important component of the new search view is the auto-completion
pane, and the task of providing completion items is delegated to
inputs through the :js:func:`~openerp.web.search.Input.complete`
method.

This method should take a single argument (the string being typed by
the user) and should fetch an ``Array`` of possible completions [#]_.

A default implementation is provided which fetches nothing.

A completion item is an object literal with two keys:

``label``

    The string which will be displayed in the completion pane. It may
    be formatted using HTML (inline only), as a result if ``value`` is
    interpolated into it it *must* be escaped. ``_.escape`` can be
    used for this.

``facet``

    Either a :js:class:`~openerp.web.search.Facet` object or (more
    commonly) the corresponding attributes object. This is the facet
    which will be inserted into the search query if the completion
    item is selected by the user.

If the ``facet`` is not provided (not present, ``null``, ``undefined``
or any other falsy value), the completion item will not be selectable
and will act as a section title of sort (the ``label`` will be
formatted differently). If an input *may* fetch multiple completion
items, it *should* prefix those with a section title using its own
name. This has no technical consequence but is clearer for users.

Providing drawer/supplementary UI
+++++++++++++++++++++++++++++++++

For some inputs (fields or not), interaction via autocompletion may be
awkward or even impossible.

These may opt to being rendered in a "drawer" as well or instead. In
that case, they will undergo the normal widget lifecycle and be
rendered inside the drawer.

.. Found no good type-based way to handle this, since there is no MI
   (so no type-tagging) and it's possible for both Field and non-Field
   input to be put into the drawer, for whatever reason (e.g. some
   sort of auto-detector completion item for date widgets, but a
   second more usual calendar widget in the drawer for more
   obvious/precise interactions)

Any input can note its desire to be rendered in the drawer by setting
its :js:attr:`~openerp.web.search.Input.in_drawer` attribute to
``true``, either on its class or on its instance.

It will be rendered in the full width of the drawer, and instantiated
only once.

.. todo:: drawer API (if a widget wants to close the drawer in some
          way), part of the low-level SearchView API/interactions?


.. todo:: handle filters and filter groups via a "driver" input which
          dynamically collects, lays out and renders filters? =>
          exercises drawer thingies

Interaction between the Search View and VisualSearch
----------------------------------------------------

The core data abstraction in VisualSearch is
:js:class:`VS.model.SearchQuery`, a backbone Collection holding
instances of the :js:class:`VS.model.SearchFacet` backbone Model.

Backbone models can hold any number of informal properties interacted
with through the :js:func:`~Backbone.Model.get` and
:js:func:`~Backbone.Model.set` methods. VisualSearch reserves three
such properties for its behavior, these properties *must* be correctly
set on all search facets created programmatically:

``app``
  a reference to the VisualSearch instance using this facet. In the
  search view, this instance is available as the
  :js:attr:`~openerp.web.SearchView.vs` attribute to the searchview
  instance.

``category``
  the *name* of the facet, displayed in the first section of a facet
  view.

``value``
  the *displayed value* of the facet, it is directly printed to the
  right of the category.

The search view uses additional keys to store state and data it needs
to associate with facet objects:

``field``
  the search field instance which created the facet, used when the
  search view needs to serialize the facets.

``json``
  the "logical" value of the facet, can be absent if the logical and
  "printable" values of the facet are the same (e.g. for a basic text
  field).

  This value may be a complex javascript object such as an array (the
  name stands for json-compatible value, it is not a JSON-encoded
  string).

.. note::

     in order to simplify getting the logical value of a search facet
     model, :js:class:`VS.model.SearchFacet` has been extended with a
     :js:func:`~VS.model.SearchFacet.value` method

Extensions and patches to VisualSearch
++++++++++++++++++++++++++++++++++++++

.. js:function:: VS.model.SearchFacet.value()

    Bundles the logic of selecting between ``json`` and ``value`` in
    order to get the logical value of a facet.

.. js:attribute:: VS.options.callbacks.make_facet

    Called by :js:class:`VS.ui.SearchBox` when it needs to create a
    new search facet *view*. By default this is not supported by
    VisualSearch, and requires monkey-patching
    :js:func:`VS.ui.SearchBox.renderFacet`.

    This patch should not alter any behavior if
    :js:attr:`~VS.options.callbacks.make_facet` is not used.

.. js:attribute:: VS.options.callbacks.make_input

    Similar to :js:attr:`~VS.options.callbacks.make_facet`, but called
    when the :js:class:`~VS.ui.SearchBox` needs to create a search
    input view. It requires monkey-patching
    :js:func:`VS.ui.SearchBox.renderSearchInput`.

Finally, :js:func:`VS.ui.SearchBox.searchEvent` is monkey-patched to
get rid of its serialize/load round-tripping of facet data: the
additional attributes needed by the search view don't round-trip (at
all) so VisualSearch must not load any data from its (fairly
simplistic) text-serialization format.

.. note::

    a second issue is that — as of `commit 3fca87101d`_ — VisualSearch
    correctly serializes facet categories containing spaces but is
    unable to load them back in. It also does not handle facets with
    *empty* categories correctly.

Loading Defaults
----------------

After loading the view data, the SearchView will call
:js:func:`openerp.web.search.Input.facet_for_defaults` on each of its
inputs with the ``defaults`` mapping of key:values (where each key
corresponds to an input). This method should look into the
``defaults`` mapping and fetch the field's default value as a
:js:class:`~VS.models.SearchFacet` if applicable.

The default implementation is to check if there is a default value for
the current input's name (via
:js:attr:`openerp.web.search.Input.attrs.name`) and if there is to
convert this value to a :js:class:`~VS.models.SearchFacet` by calling
:js:func:`openerp.web.search.Input.facet_for`.

There is no built-in (default) implementation of
:js:func:`openerp.web.search.Input.facet_for`. This method should
fetch the :js:class:`~VS.models.SearchFacet` corresponding to the
"raw" value passed as argument.

Providing auto-completion
-------------------------

An important component of the unified search view is the faceted
autocompletion pane. In order to provide good user and developer
experiences, this pane is pluggable (value-wise): each and every
control of the search view can check for (and provide) categorized
auto-completions for a given value being typed by the user.

This is done by implementing
:js:func:`openerp.web.search.Input.complete`: the method is provided
with a value to complete, and should fetch an ``Array`` of completion
values. These completion values will then be provided to the global
autocompletion list, implemented via `jquery-ui autocomplete
<http://jqueryui.com/demos/autocomplete/>`_.

Because the search view uses a custom renderer for its completion, it
was possible to fix some incompatibilities between the attributes of
completion items and VisualSearch's facet model:

Actual completion items
+++++++++++++++++++++++

These are selectable items, and upon selection are turned into actual
search facet objects. They should have all the properties of a search
facet (as described above) and can have one more optional property:
``label``.

When rendering an item in the list, the renderer will first try to use
the ``label`` property if it exists (``label`` can contain HTML and
will be inserted as-is, so it can bold or emphasize some of its
elements), if it does not the ``value`` property will be used.

.. note:: the ``app`` key should not be specified on completion item,
          it will be set automatically when the search view creates
          the facet from the item.

Section titles
++++++++++++++

A second kind of completion values is the section titles. Section
titles are similar to completion items but only have a ``category``
property. They will be rendered in a different style and can not be
selected in the auto-completion (they will be skipped).

.. note::

    Technically, section title items can have any property they want
    *as long as they do not have a value property*. A ``value``
    property set to ``false``, ``null`` or ``undefined`` is **not**
    equivalent to not having a ``value`` property.

If an input *may* fetch more than one completion item, it *should*
prepend a section title (using its own name) to the completion items.

Converting from facet objects
-----------------------------

Ultimately, the point of the search view is to allow searching. In
OpenERP this is done via :ref:`domains <openerpserver:domains>`. On
the other hand, the OpenERP Web 7 search view's state is modelled
after a collection of :js:class:`~VS.model.SearchFacet`, and each
field of a search view may have special requirements when it comes to
the domains it produces [#]_.

So there needs to be some way of mapping
:js:class:`~VS.model.SearchFacet` objects to OpenERP search data.

This is done via an input's
:js:func:`~openerp.web.search.Input.get_domain` and
:js:func:`~openerp.web.search.Input.get_context`. Each takes a
:js:class:`~VS.model.SearchFacet` and returns whatever it's supposed
to generate (a domain or a context, respectively). Either can return
``null`` if the current value does not map to a domain or context, and
can throw an :js:class:`~openerp.web.search.Invalid` exception if the
value is not valid at all for the field.

Converting to facet objects
---------------------------

Changes
-------

.. todo:: merge in changelog instead

The displaying of the search view was significantly altered from
OpenERP Web 6.1 to OpenERP Web 7.

As a result, while the external API used to interact with the search
view does not change many internal details — including the interaction
between the search view and its widgets — were significantly altered:

Internal operations
+++++++++++++++++++

* :js:func:`openerp.web.SearchView.do_clear` has been removed
* :js:func:`openerp.web.SearchView.do_toggle_filter` has been removed

Widgets API
+++++++++++

* :js:func:`openerp.web.search.Widget.render` has been removed

* :js:func:`openerp.web.search.Widget.make_id` has been removed

* Search field objects are not openerp widgets anymore, their
  ``start`` is not generally called

* :js:func:`~openerp.web.search.Input.clear` has been removed since
  clearing the search view now simply consists of removing all search
  facets

* :js:func:`~openerp.web.search.Input.get_domain` and
  :js:func:`~openerp.web.search.Input.get_context` now take a
  :js:class:`~VS.model.SearchFacet` as parameter, from which it's
  their job to get whatever value they want

* :js:func:`~openerp.web.search.Input.get_groupby` has been added. It returns
  an :js:class:`Array` of context-like constructs. By default, it does not do
  anything in :js:class:`~openerp.web.search.Field` and it returns the various
  contexts of its enabled filters in
  :js:class:`~openerp.web.search.FilterGroup`.

Filters
+++++++

* :js:func:`openerp.web.search.Filter.is_enabled` has been removed

* :js:class:`~openerp.web.search.FilterGroup` instances are still
  rendered (and started) in the "advanced search" drawer.

Fields
++++++

* ``get_value`` now takes a :js:class:`~VS.model.SearchFacet` (instead
  of taking no argument).

  A default implementation is provided as
  :js:func:`openerp.web.search.Field.get_value` and simply calls
  :js:func:`VS.model.SearchFacet.value`.

* The third argument to
  :js:func:`~openerp.web.search.Field.make_domain` is now the
  :js:class:`~VS.model.SearchFacet` received by
  :js:func:`~openerp.web.search.Field.get_domain`, so child classes
  have all the information they need to derive the "right" resulting
  domain.

Custom filters
++++++++++++++

Instead of being an intrinsic part of the search view, custom filters
are now a special case of filter groups. They are treated specially
still, but much less so than they used to be.

Many To One
+++++++++++

* Because the autocompletion service is now provided by the search
  view itself,
  :js:func:`openerp.web.search.ManyToOneField.setup_autocomplete` has
  been removed.

.. [#] the original view was implemented on top of a monkey-patched
       VisualSearch, but as our needs diverged from VisualSearch's goal this
       made less and less sense ultimately leading to a clean-room
       reimplementation

.. [#] In case you are extending the search view with a brand new type
       of input

.. [#] Ideally this array should not hold more than about 10 items,
       but the search view does not put any constraint on this at the
       moment. Note that this may change.

.. [#] search view fields may also bundle context data to add to the
       search context

.. _commit 3fca87101d:
     https://github.com/documentcloud/visualsearch/commit/3fca87101d
