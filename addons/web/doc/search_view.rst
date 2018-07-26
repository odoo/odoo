Search View
===========

OpenERP Web 7.0 implements a unified facets-based search view instead
of the previous form-like search view (composed of buttons and
multiple fields). The goal for this change is twofold:

* Avoid the common issue of users confusing the search view with a
  form view and trying to create their records through it (or entering
  all their data, hitting the ``Create`` button expecting their record
  to be created and losing everything).

* Improve the looks and behaviors of the view, and the fit within
  OpenERP Web's new design.

The internal structure of the faceted search is inspired by
`VisualSearch <http://documentcloud.github.com/visualsearch/>`_
[#previous]_.

As does VisualSearch, the new search view is based on `Backbone`_ and
makes significant use of Backbone's models and collections (OpenERP
Web's widgets make a good replacement for Backbone's own views). As a
result, understanding the implementation details of the OpenERP Web 7
search view also requires a basic understanding of Backbone's models,
collections and events.

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

Search view inputs have four main roles:

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
:js:func:`openerp.web.search.Input.facet_for` [#no_impl]_, but
:js:class:`openerp.web.search.Field` provides one, which uses the
value as-is to fetch a :js:class:`~openerp.web.search.Facet`.

Providing completions
+++++++++++++++++++++

An important component of the new search view is the auto-completion
pane, and the task of providing completion items is delegated to
inputs through the :js:func:`~openerp.web.search.Input.complete`
method.

This method should take a single argument (the string being typed by
the user) and should fetch an ``Array`` of possible completions
[#completion]_.

A default implementation is provided which fetches nothing.

A completion item is a javascript object with two keys (technically it
can have any number of keys, but only these two will be used by the
search view):

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

.. note::

    If a field is :js:func:`invisible
    <openerp.web.search.Input.visible>`, its completion function will
    *not* be called.

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

Any input can note its desire to be rendered in the drawer by
returning a truthy value from
:js:func:`~openerp.web.search.Input.in_drawer`.

By default, :js:func:`~openerp.web.search.Input.in_drawer` returns the
value of :js:attr:`~openerp.web.search.Input._in_drawer`, which is
``false``. The behavior can be toggled either by redefining the
attribute to ``true`` (either on the class or on the input), or by
overriding :js:func:`~openerp.web.search.Input.in_drawer` itself.

The input will be rendered in the full width of the drawer, it will be
started only once (per view).

.. todo:: drawer API (if a widget wants to close the drawer in some
          way), part of the low-level SearchView API/interactions?


.. todo:: handle filters and filter groups via a "driver" input which
          dynamically collects, lays out and renders filters? =>
          exercises drawer thingies

.. note::

    An :js:func:`invisible <openerp.web.search.Input.visible>` input
    will not be inserted into the drawer.

Converting from facet objects
+++++++++++++++++++++++++++++

Ultimately, the point of the search view is to allow searching. In
OpenERP this is done via :ref:`domains <openerpserver:domains>`. On
the other hand, the OpenERP Web 7 search view's state is modelled
after a collection of :js:class:`~openerp.web.search.Facet`, and each
field of a search view may have special requirements when it comes to
the domains it produces [#special]_.

So there needs to be some way of mapping
:js:class:`~openerp.web.search.Facet` objects to OpenERP search data.

This is done via an input's
:js:func:`~openerp.web.search.Input.get_domain` and
:js:func:`~openerp.web.search.Input.get_context`. Each takes a
:js:class:`~openerp.web.search.Facet` and returns whatever it's
supposed to generate (a domain or a context, respectively). Either can
return ``null`` if the current value does not map to a domain or
context, and can throw an :js:class:`~openerp.web.search.Invalid`
exception if the value is not valid at all for the field.

.. note::

    The :js:class:`~openerp.web.search.Facet` object can have any
    number of values (from 1 upwards)

.. note::

    There is a third conversion method,
    :js:func:`~openerp.web.search.Input.get_groupby`, which returns an
    ``Array`` of groupby domains rather than a single context. At this
    point, it is only implemented on (and used by) filters.

Programmatic interactions: internal model
-----------------------------------------

This new searchview is built around an instance of
:js:class:`~openerp.web.search.SearchQuery` available as
:js:attr:`openerp.web.SearchView.query`.

The query is a `backbone collection`_ of
:js:class:`~openerp.web.search.Facet` objects, which can be interacted
with directly by external objects or search view controls
(e.g. widgets displayed in the drawer).

.. js:class:: openerp.web.search.SearchQuery

    The current search query of the search view, provides convenience
    behaviors for manipulating :js:class:`~openerp.web.search.Facet`
    on top of the usual `backbone collection`_ methods.

    The query ensures all of its facets contain at least one
    :js:class:`~openerp.web.search.FacetValue` instance. Otherwise,
    the facet is automatically removed from the query.

    .. js:function:: openerp.web.search.SearchQuery.add(values, options)

        Overridden from the base ``add`` method so that adding a facet
        which is *already* in the collection will merge the value of
        the new facet into the old one rather than add a second facet
        with different values.

        :param values: facet, facet attributes or array thereof
        :returns: the collection itself

    .. js:function:: openerp.web.search.SearchQuery.toggle(value, options)

        Convenience method for toggling facet values in a query:
        removes the values (through the facet itself) if they are
        present, adds them if they are not. If the facet itself is not
        in the collection, adds it automatically.

        A toggling is atomic: only one change event will be triggered
        on the facet regardless of the number of values added to or
        removed from the facet (if the facet already exists), and the
        facet is only removed from the query if it has no value *at
        the end* of the toggling.

        :param value: facet or facet attributes
        :returns: the collection

.. js:class:: openerp.web.search.Facet

    A `backbone model`_ representing a single facet of the current
    search. May map to a search field, or to a more complex or
    fuzzier input (e.g. a custom filter or an advanced search).

    .. js:attribute:: category

        The displayed name of the facet, as a ``String``. This is a
        backbone model attribute.

    .. js:attribute:: field

        The :js:class:`~openerp.web.search.Input` instance which
        originally created the facet [#facet-field]_, used to delegate
        some operations (such as serializing the facet's values to
        domains and contexts). This is a backbone model attribute.

    .. js:attribute:: values

        :js:class:`~openerp.web.search.FacetValues` as a javascript
        attribute, stores all the values for the facet and helps
        propagate their events to the facet. Is also available as a
        backbone attribute (via ``#get`` and ``#set``) in which cases
        it serializes to and deserializes from javascript arrays (via
        ``Collection#toJSON`` and ``Collection#reset``).

    .. js:attribute:: [icon]

        optional, a single ASCII letter (a-z or A-Z) mapping to the
        bundled mnmliconsRegular icon font.

        When a facet with an ``icon`` attribute is rendered, the icon
        is displayed (in the icon font) in the first section of the
        facet instead of the ``category``.

        By default, only filters make use of this facility.

.. js:class:: openerp.web.search.FacetValues

    `Backbone collection`_ of
    :js:class:`~openerp.web.search.FacetValue` instances.

.. js:class:: openerp.web.search.FacetValue

    `Backbone model`_ representing a single value within a facet,
    represents a pair of (displayed name, logical value).

    .. js:attribute:: label

        Backbone model attribute storing the "displayable"
        representation of the value, visually output to the
        user. Must be a string.

    .. js:attribute:: value

        Backbone model attribute storing the logical/internal value
        (of itself), will be used by
        :js:class:`~openerp.web.search.Input` to serialize to domains
        and contexts.

        Can be of any type.

Field services
--------------

:js:class:`~openerp.web.search.Field` provides a default
implementation of :js:func:`~openerp.web.search.Input.get_domain` and
:js:func:`~openerp.web.search.Input.get_context` taking care of most
of the peculiarities pertaining to OpenERP's handling of fields in
search views. It also provides finer hooks to let developers of new
fields and widgets customize the behavior they want without
necessarily having to reimplement all of
:js:func:`~openerp.web.search.Input.get_domain` or
:js:func:`~openerp.web.search.Input.get_context`:

.. js:function:: openerp.web.search.Field.get_context(facet)

    If the field has no ``@context``, simply returns
    ``null``. Otherwise, calls
    :js:func:`~openerp.web.search.Field.value_from` once for each
    :js:class:`~openerp.web.search.FacetValue` of the current
    :js:class:`~openerp.web.search.Facet` (in order to extract the
    basic javascript object from the
    :js:class:`~openerp.web.search.FacetValue` then evaluates
    ``@context`` with each of these values set as ``self``, and
    returns the union of all these contexts.

    :param facet:
    :type facet: openerp.web.search.Facet
    :returns: a context (literal or compound)

.. js:function:: openerp.web.search.Field.get_domain(facet)

    If the field has no ``@filter_domain``, calls
    :js:func:`~openerp.web.search.Field.make_domain` once with each
    :js:class:`~openerp.web.search.FacetValue` of the current
    :js:class:`~openerp.web.search.Facet` as well as the field's
    ``@name`` and either its ``@operator`` or
    :js:attr:`~openerp.web.search.Field.default_operator`.

    If the field has an ``@filter_value``, calls
    :js:func:`~openerp.web.search.Field.value_from` once per
    :js:class:`~openerp.web.search.FacetValue` and evaluates
    ``@filter_value`` with each of these values set as ``self``.

    In either case, "ors" all of the resulting domains (using ``|``)
    if there is more than one
    :js:class:`~openerp.web.search.FacetValue` and returns the union
    of the result.

    :param facet:
    :type facet: openerp.web.search.Facet
    :returns: a domain (literal or compound)

.. js:function:: openerp.web.search.Field.make_domain(name, operator, facetValue)

    Builds a literal domain from the provided data. Calls
    :js:func:`~openerp.web.search.Field.value_from` on the
    :js:class:`~openerp.web.search.FacetValue` and evaluates and sets
    it as the domain's third value, uses the other two parameters as
    the first two values.

    Can be overridden to build more complex default domains.

    :param String name: the field's name
    :param String operator: the operator to use in the field's domain
    :param facetValue:
    :type facetValue: openerp.web.search.FacetValue
    :returns: Array<(String, String, Object)>

.. js:function:: openerp.web.search.Field.value_from(facetValue)

    Extracts a "bare" javascript value from the provided
    :js:class:`~openerp.web.search.FacetValue`, and returns it.

    The default implementation will simply return the ``value``
    backbone property of the argument.

    :param facetValue:
    :type facetValue: openerp.web.search.FacetValue
    :returns: Object

.. js:attribute:: openerp.web.search.Field.default_operator

    Operator used to build a domain when a field has no ``@operator``
    or ``@filter_domain``. ``"="`` for
    :js:class:`~openerp.web.search.Field`

Arbitrary data storage
----------------------

:js:class:`~openerp.web.search.Facet` and
:js:class:`~openerp.web.search.FacetValue` objects (and structures)
provided by your widgets should never be altered by the search view
(or an other widget). This means you are free to add arbitrary fields
in these structures if you need to (because you have more complex
needs than the attributes described in this document).

Ideally this should be avoided, but the possibility remains.

Changes
-------

.. todo:: merge in changelog instead?

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
  :js:class:`~openerp.web.search.Facet` as parameter, from which it's
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

* ``get_value`` has been replaced by
  :js:func:`~openerp.web.search.Field.value_from` as it now takes a
  :js:class:`~openerp.web.search.FacetValue` argument (instead of no
  argument). It provides a default implementation returning the
  ``value`` property of its argument.

* The third argument to
  :js:func:`~openerp.web.search.Field.make_domain` is now a
  :js:class:`~openerp.web.search.FacetValue` so child classes have all
  the information they need to derive the "right" resulting domain.

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

Advanced Search
+++++++++++++++

* The advanced search is now a more standard
  :js:class:`~openerp.web.search.Input` configured to be rendered in
  the drawer.

* :js:class:`~openerp.web.search.ExtendedSearchProposition.Field` are
  now standard widgets, with the "right" behaviors (they don't rebind
  their ``$element`` in ``start()``)

* The ad-hoc optional setting of the openerp field descriptor on a
  :js:class:`~openerp.web.search.ExtendedSearchProposition.Field` has
  been removed, the field descriptor is now passed as second argument
  to the
  :js:class:`~openerp.web.search.ExtendedSearchProposition.Field`'s
  constructor, and bound to its
  :js:attr:`~openerp.web.search.ExtendedSearchProposition.Field.field`.

* Instead of its former domain triplet ``(field, operator, value)``,
  :js:func:`~openerp.web.search.ExtendedSearchProposition.get_proposition`
  now returns an object with two fields ``label`` and ``value``,
  respectively a human-readable version of the proposition and the
  corresponding domain triplet for the proposition.

.. [#previous]

    the original view was implemented on top of a monkey-patched
    VisualSearch, but as our needs diverged from VisualSearch's goal
    this made less and less sense ultimately leading to a clean-room
    reimplementation

.. [#no_impl]

    In case you are extending the search view with a brand new type of
    input

.. [#completion]

    Ideally this array should not hold more than about 10 items, but
    the search view does not put any constraint on this at the
    moment. Note that this may change.

.. [#facet-field]

    ``field`` does not actually need to be an instance of
    :js:class:`~openerp.web.search.Input`, nor does it need to be what
    created the facet, it just needs to provide the three
    facet-serialization methods
    :js:func:`~openerp.web.search.Input.get_domain`,
    :js:func:`~openerp.web.search.Input.get_context` and
    :js:func:`~openerp.web.search.Input.get_gropuby`, existing
    :js:class:`~openerp.web.search.Input` subtypes merely provide
    convenient base implementation for those methods.

    Complex search view inputs (especially those living in the drawer)
    may prefer using object literals with the right slots returning
    closed-over values or some other scheme un-bound to an actual
    :js:class:`~openerp.web.search.Input`, as
    :js:class:`~openerp.web.search.CustomFilters` and
    :js:class:`~openerp.web.search.Advanced` do.

.. [#special]

    search view fields may also bundle context data to add to the
    search context

.. _Backbone:
    http://documentcloud.github.com/backbone/

.. _Backbone.Collection:
.. _Backbone collection:
    http://documentcloud.github.com/backbone/#Collection

.. _Backbone model:
    http://documentcloud.github.com/backbone/#Model

.. _commit 3fca87101d:
    https://github.com/documentcloud/visualsearch/commit/3fca87101d
