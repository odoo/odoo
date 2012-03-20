Search View
===========

Loading Defaults
----------------

After loading the view data, the SearchView will call
:js:func:`openerp.web.search.Input.facet_for_defaults` with the ``defaults``
mapping of key:values (where each key corresponds to an input).

The default implementation is to check if there is a default value for the
current input's name (via :js:attr:`openerp.web.search.Input.attrs.name`) and
if there is to convert this value to a :js:class:`VS.models.SearchFacet` by
calling :js:func:`openerp.web.search.Input.facet_for`.

Both methods should return a ``jQuery.Deferred<Null|VS.model.SearchFacet>``.

There is no built-in (default) implementation of
:js:func:`openerp.web.search.Input.facet_for`.

Providing auto-completion
-------------------------

An important component of the unified search view is the faceted autocompletion
pane. In order to provide good user and developer experiences, this pane is
pluggable (value-wise): each and every control of the search view can check for
(and provide) categorized auto-completions for a given value being typed by
the user.

This is done by implementing :js:func:`openerp.web.search.Input.complete`: the
method is provided with a value to complete, and the input must either return
a ``jQuery.Deferred<Null>`` or fetch (by returning a ``jQuery.Deferred``) an
array of completion values.

.. todo:: describe the shape of "completion values"?

Converting to and from facet objects
------------------------------------

Changes
-------

.. todo:: merge in changelog instead

The displaying of the search view was significantly altered from OpenERP Web
6.1 to OpenERP Web 6.2: it went form a form-like appearance (inherited from
previous web client versions and ultimately from the GTK client) to a
"universal" search input with facets.

As a result, while the external API used to interact with the search view does
not change the internal details — including the interaction between the search
view and its widgets — is significantly altered:

Widgets API
+++++++++++

* :js:func:`openerp.web.search.Widget.render` has been removed
* Search field objects are not openerp widgets anymore, their ``start`` is
  not generally called

Filters
+++++++

* :js:func:`openerp.web.search.Filter.is_enabled` has been removed

Many To One
+++++++++++

* Because the autocompletion service is now provided by the search view
  itself, :js:func:`openerp.web.search.ManyToOneField.setup_autocomplete` has
  been removed.
