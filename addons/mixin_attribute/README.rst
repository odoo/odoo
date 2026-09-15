================
Attribute Mixins
================

Reusable EAV (Entity-Attribute-Value) abstract mixins, meant to be inherited
by concrete attribute families defined in consuming modules.

Ships mixins only: no concrete models, no data, no views. The shape is derived
from ``product``'s attribute engine, which is the mature implementation in the
tree; ``product`` consumes these mixins rather than duplicating them.

Mixins
======

* ``mixin.attribute`` -- the attribute (dimension): ``name``, ``sequence``,
  ``active``, ``value_type`` and ``display_type``. Concrete models add their
  own ``value_ids`` One2many pointing at their value model.
* ``mixin.attribute.value`` -- a value: ``name``, ``sequence``, ``color``
  (defaulted across the palette by ``_default_color``), ``active``, and a
  ``display_name`` qualified with the attribute. Concrete models add
  ``attribute_id``.
* ``mixin.attribute.line`` -- one attribute plus its chosen values, bound to a
  subject record: ``sequence``, ``active``, ``value_count``, and the
  ``_check_values`` coherence constraint. Concrete models declare the parent
  Many2one, ``attribute_id``, ``value_ids`` and their own ``_rec_name``.

``value_type`` vs ``display_type``
==================================

They are orthogonal and both belong on the attribute:

* ``value_type`` (``single`` / ``multi``) is a **data rule** -- how many values
  one line may hold.
* ``display_type`` (``radio`` / ``pills`` / ``select`` / ``color`` / ``multi``
  / ``image``) only picks the **widget**. A ``single`` attribute may still
  render as radio, pills, select or colour swatches.

What ``single`` means depends on what a line *is* for the subject, and consumers
differ:

* Where a line is the **offer** -- a product template listing the values it
  sells -- the line legitimately holds many values and the choice of one is
  made downstream, per variant. ``product.attribute`` therefore defaults
  ``value_type`` to ``multi``.
* Where a line is the **selection** -- a surface or a partner recording what it
  actually is -- ``single`` means exactly one value on the line.

Hooks a consumer can set
========================

``attribute.mixin._attribute_line_model``
  Name of the concrete line model, e.g. ``"product.template.attribute.line"``.
  **Set this.** ``_check_values`` is an ``@api.constrains`` on the *line*, and
  the ORM has no cross-model constrains, so nothing re-runs it when the
  *attribute* changes. Without this hook, flipping ``value_type`` from
  ``multi`` to ``single`` left every existing multi-value line silently
  violating the rule the constraint exists to enforce.

``attribute.line.mixin._requires_value``
  Whether an active line must hold at least one value. ``True`` where the line
  is the offer (an empty one says nothing); ``False`` -- the default -- where a
  line is a slot awaiting capture.

``attribute.line.mixin._subject_label()``
  Human name of the record the line hangs off, used to qualify coherence
  errors ("... for *Chair*"). Empty by default; override where users need one
  record disambiguated from thousands.

``attribute.value.mixin._default_color()``
  Palette index for a new value. Defaults to a random 1-11 so values are
  visually distinguishable; ``0`` means "no colour" and is not drawn.

``_filtered_used()`` (on the attribute and value mixins)
  Which of ``self`` is already bound to a subject. The default answers "some
  attribute line references it". Override to narrow it -- ``product`` counts
  only lines of *active* templates, so an attribute whose sole trace is an
  archived product stays deletable.

``_usage_label()`` (on the attribute and value mixins)
  Names the subjects holding the record, used to qualify the guard messages
  ("... because it is used on: *Chair*"). Empty by default, which selects a
  shorter sentence.

In-use protection
=================

Deleting an attribute cascades its values away and takes every captured line
with them; archiving one hides it from the pickers while the lines holding it
stay live. Both are silent data loss, so the mixins refuse:

* ``mixin.attribute`` -- ``@api.ondelete`` and ``action_archive`` guards.
* ``mixin.attribute.value`` -- an ``@api.ondelete`` guard, and a ``write``
  guard refusing to re-home a value in use (the lines point at the value, not
  at the attribute/value pair, so moving it leaves every one of them stray --
  a violation ``_check_values`` cannot see, because the write lands on the
  value).

All of them resolve "in use" through ``_filtered_used()``, so a consumer tunes
the policy in one place. ``_in_use_message()`` returns the same sentence
without raising, for a UI that wants to grey out a button rather than fail the
click; ``product`` exposes it over RPC as ``check_is_used_on_products``.

The guards are inert until ``_attribute_line_model`` is set -- with no line
model there is nothing to be in use *by*.

Both guards are all-or-nothing over the whole call: archiving or deleting a
multi-record recordset where even one record is in use refuses the entire
batch, including the records that are not in use and would otherwise be safe
on their own. This is deliberate -- a partial success (some records archived,
others rejected) has its own surprise potential for a multi-select UI action --
not a per-record filter that was forgotten.

Name uniqueness
===============

A consumer must not declare this as a plain ``UNIQUE(name)`` /
``UNIQUE(attribute_id, name)`` constraint -- ``name`` is ``translate=True``, so
it is stored as a ``jsonb`` column and a UNIQUE constraint compares whole
translation *documents* rather than names. Two records both called "Whitefly"
are distinct rows the moment their translation sets differ -- and they differ
as soon as a second language is active, because Odoo writes the active
language alongside the source term on create. A user working in Spanish
creating "Mosca blanca" stores ``{"en_US": .., "es_MX": ..}`` where an English
colleague stored ``{"en_US": ..}``, and the constraint sees no duplicate.

The rule has to compare the *source term*, which means an expression, and
PostgreSQL does not allow expressions in a UNIQUE constraint over a plain
column, so the enforcement point is a ``models.UniqueIndex`` over
``(name->>'en_US')`` -- but which side declares it differs per mixin:

* ``mixin.attribute`` declares **none of its own**: it inherits
  ``mixin.catalog``'s unscoped ``name_uniq_index()``, so a consumer's
  attributes are unique by name across the whole model. A consumer whose
  names are legitimately reused across differently-scoped catalogs opts out
  with ``no_name_uniq_index()`` on the concrete model, as ``product.attribute``
  does.
* ``mixin.attribute.value`` **already declares one**, scoped to
  ``attribute_id`` (``_name_src_uniq = name_uniq_index("attribute_id", ...)``
  in ``mixin_attribute_value.py``), because a value is only unique within its
  attribute -- "Large" belongs to both Size and Format. A consumer must **not**
  add a second index here: the mixin's own index is already the scoped one
  this section used to ask consumers to write themselves.

Gotcha: unstated field attributes are inherited
===============================================

Odoo merges field attributes across the MRO, so an attribute a consumer does
*not* restate is taken from the mixin. Redeclaring ``sequence`` to add an index
does not reset its ``default`` -- the mixin's ``10`` still applies. Restate any
attribute you need to differ.

Depends
=======

``base``.
