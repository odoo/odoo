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

The faceted search is implemented through a monkey-patched
`VisualSearch <http://documentcloud.github.com/visualsearch/>`_
[#]_. VisualSearch is based on `Backbone
<http://documentcloud.github.com/backbone/>`_ and makes significant
use of Backbone's models and views. As a result, understanding the
implementation of the OpenERP Web 6.2 search view also requires a
basic understanding of Backbone.

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
  view. The category *may* be ``null``.

``value``
  the *displayed value* of the facet, it is directly printed to the
  right of the category.

The search view uses additional keys to store state and data it needs
to associate with facet objects:

``field``
  the search field instance which created the facet, optional. May or
  may not be inferrable from ``category``.

``json``
  the "logical" value of the facet, can be absent if the logical and
  "printable" values of the facet are the same (e.g. for a basic text
  field).

  This value may be a complex javascript object such as an array or an
  object (the name stands for json-compatible value, it is not
  JSON-encoded).

.. note::

     in order to simplify fetching an actual value from a search facet
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
simplistic) text-serialization format

.. note::

    a second issue is that — as of `commit 3fca87101d`_ — VisualSearch
    correctly serializes facet categories containing spaces but is
    unable to load them back in. It also does not handle facets with
    *empty* categories correctly.

Loading Defaults
----------------

After loading the view data, the SearchView will call
:js:func:`openerp.web.search.Input.facet_for_defaults` with the
``defaults`` mapping of key:values (where each key corresponds to an
input).

The default implementation is to check if there is a default value for
the current input's name (via
:js:attr:`openerp.web.search.Input.attrs.name`) and if there is to
convert this value to a :js:class:`VS.models.SearchFacet` by calling
:js:func:`openerp.web.search.Input.facet_for`.

Both methods should return a
``jQuery.Deferred<Null|VS.model.SearchFacet>``.

There is no built-in (default) implementation of
:js:func:`openerp.web.search.Input.facet_for`.

Providing auto-completion
-------------------------

An important component of the unified search view is the faceted
autocompletion pane. In order to provide good user and developer
experiences, this pane is pluggable (value-wise): each and every
control of the search view can check for (and provide) categorized
auto-completions for a given value being typed by the user.

This is done by implementing
:js:func:`openerp.web.search.Input.complete`: the method is provided
with a value to complete, and the input must either return a
``jQuery.Deferred<Null>`` or fetch (by returning a
``jQuery.Deferred``) an array of completion values.

.. todo:: describe the shape of "completion values"?

Converting to and from facet objects
------------------------------------

Changes
-------

.. todo:: merge in changelog instead

The displaying of the search view was significantly altered from
OpenERP Web 6.1 to OpenERP Web 6.2.

As a result, while the external API used to interact with the search
view does not change the internal details — including the interaction
between the search view and its widgets — is significantly altered:

Widgets API
+++++++++++

* :js:func:`openerp.web.search.Widget.render` has been removed

* Search field objects are not openerp widgets anymore, their
  ``start`` is not generally called

Filters
+++++++

* :js:func:`openerp.web.search.Filter.is_enabled` has been removed

Many To One
+++++++++++

* Because the autocompletion service is now provided by the search
  view itself,
  :js:func:`openerp.web.search.ManyToOneField.setup_autocomplete` has
  been removed.

.. [#] the library code is untouched, all patching is performed in the
       Search view's implementation module. Changes to the
       VisualSearch code should only update the library to new
       revisions or releases.
.. _commit 3fca87101d:
     https://github.com/documentcloud/visualsearch/commit/3fca87101d
