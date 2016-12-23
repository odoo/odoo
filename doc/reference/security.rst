:banner: banners/security.jpg

.. _reference/security:

================
Security in Odoo
================

Aside from manually managing access using custom code, Odoo provides two main
data-driven mechanisms to manage or restrict access to data.

Both mechanisms are linked to specific users through *groups*: a user belongs
to any number of groups, and security mechanisms are associated to groups,
thus applying security mechamisms to users.

.. _reference/security/acl:

Access Control
==============

Managed by the ``ir.model.access`` records, defines access to a whole model.

Each access control has a model to which it grants permissions, the
permissions it grants and optionally a group.

Access controls are additive, for a given model a user has access all
permissions granted to any of its groups: if the user belongs to one group
which allows writing and another which allows deleting, they can both write
and delete.

If no group is specified, the access control applies to all users, otherwise
it only applies to the members of the given group.

Available permissions are creation (``perm_create``), searching and reading
(``perm_read``), updating existing records (``perm_write``) and deleting
existing records (``perm_unlink``)

.. _reference/security/rules:

Record Rules
============

Record rules are conditions that records must satisfy for an operation
(create, read, update or delete) to be allowed. It is applied record-by-record
after access control has been applied.

A record rule has:

* a model on which it applies
* a set of permissions to which it applies (e.g. if ``perm_read`` is set, the
  rule will only be checked when reading a record)
* a set of user groups to which the rule applies, if no group is specified
  the rule is *global*
* a :ref:`domain <reference/orm/domains>` used to check whether a given record
  matches the rule (and is accessible) or does not (and is not accessible).
  The domain is evaluated with two variables in context: ``user`` is the
  current user's record and ``time`` is the `time module`_

Global rules and group rules (rules restricted to specific groups versus
groups applying to all users) are used quite differently:

* Global rules are subtractive, they *must all* be matched for a record to be
  accessible
* Group rules are additive, if *any* of them matches (and all global rules
  match) then the record is accessible

This means the first *group rule* restricts access, but any further
*group rule* expands it, while *global rules* can only ever restrict access
(or have no effect).

.. warning:: record rules do not apply to the Administrator user
    :class: aphorism

    although access rules do

.. _reference/security/fields:

Field Access
============

.. versionadded:: 7.0

An ORM :class:`~odoo.fields.Field` can have a ``groups`` attribute
providing a list of groups (as a comma-separated string of
:term:`external identifiers`).

If the current user is not in one of the listed groups, he will not have
access to the field:

* restricted fields are automatically removed from requested views
* restricted fields are removed from :meth:`~odoo.models.Model.fields_get`
  responses
* attempts to (explicitly) read from or write to restricted fields results in
  an access error

.. todo::

    field access groups apply to administrator in fields_get but not in
    read/write...

.. _foo: http://google.com
.. _time module: https://docs.python.org/2/library/time.html
