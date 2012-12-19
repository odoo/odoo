.. _performing_joins_in_select:

Perfoming joins in select
=========================

.. versionadded:: 7.0

Starting with OpenERP 7.0, an ``auto_join`` attribute is added on *many2one* and
*one2many* fields. The purpose is to allow the automatic generation of joins in
select queries. This attribute is set to False by default, therefore not changing
the default behavior. Please note that we consider this feature as still experimental
and should be used only if you understand its limitations and targets.

Without ``_auto_join``, the behavior of expression.parse() is the same as before.
Leafs holding a path beginning with many2one or one2many fields perform a search
on the relational table. The result is then used to replace the leaf content.
For example, if you have on res.partner a domain like ``[('bank_ids.name',
'like', 'foo')]`` with bank_ids linking to res.partner.bank, 3 queries will be
performed :

- 1 on res_partner_bank, with domain ``[('name', '=', 'foo')]``, that returns a
  list of res.partner.bank ids (bids)
- 1 on res_partner, with a domain ``['bank_ids', 'in', bids)]``, that returns a
  list of res.partner ids (pids)
- 1 on res_partner, with a domain ``[('id', 'in', pids)]``

When the ``auto_join`` attribute is True on a relational field, the destination
table will be joined to produce only one query.

- the relational table is accessed using an alias: ``'"res_partner_bank"
  as res_partner__bank_ids``. The alias is generated using the relational field
  name. This allows to have multiple joins with different join conditions on the
  same table, depending on the domain.
- there is a join condition between the destination table and the main table:
  ``res_partner__bank_ids."partner_id"=res_partner."id"``
- the condition is then written on the relational table:
  ``res_partner__bank_ids."name" = 'foo'``

This manipulation is performed in expression.parse(). It checks leafs that
contain a path, i.e. any domain containing a '.'. It then  checks whether the
first item of the path is a *many2one* or *one2many* field with the ``auto_join``
attribute set. If set, it adds a join query and recursively analyzes the
remaining of the leaf, using the same behavior. If the remaining path also holds
a path with auto_join fields, it will add all tables and add every necessary
join conditions.

Chaining joins allows to reduce the number of queries performed, and to avoid
having too long equivalent leaf replacement in domains. Indeed, the internal
queries produced by this behavior can be very costly, because they were generally
select queries without limit that could lead to huge ('id', 'in', [...])
leafs to analyze and execute.

Some limitations exist on this feature that limits its current use as of version
7.0. **This feature is therefore considered as experimental, and used
to speedup some precise bottlenecks in OpenERP**.

List of known issues and limitations:

- using ``auto_join`` bypasses the business logic; no name search is performed,
  only direct matches between ids using join conditions
- ir.rules are not taken into account when analyzing and adding the join
  conditions

List of already-supported corner cases :

- one2many fields having a domain attribute. Static domains as well as dynamic
  domain are supported
- auto_join leading to functional searchable fields

Typical use in OpenERP 7.0:

- in mail module: notification_ids field on mail_message, allowing to speedup
  the display of the various mailboxes
- in mail module: message_ids field on mail_thread, allowing to speedup the
  display of needaction counters and documents having unread messages
