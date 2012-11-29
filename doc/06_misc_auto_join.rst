.. _performing_joins_in_select:

Perfoming joins in select
=========================

.. versionadded:: 7.0

Starting with OpenERP 7.0, an ``_auto_join`` attribute is added on *many2one* and
*one2many* fields. The purpose is to allow the automatic generation of joins in
select queries. This attribute is set to False by default, therefore not changing
the default behavior of those fields. It is not recommended to use this attribute
unless you understand the limitations of the feature.

Without ``_auto_join``, the behavior of expression.parse() is the same as before.
Leafs holding a path beginning with many2one or one2many fields perform a search
on the relational table. The result is then used to replace the leaf content.
For example, if you have on res.partner a domain like ``[('bank_ids.name',
'like', 'foo')]`` with bank_ids linking to res.partner.bank, 3 queries will be
performed :

- 1 on res_partner_bank, with domain ``[('name', '=', 'foo')]``, that returns a
  list of (res.partner.bank) bids
- 1 on res_partner, with a domain ``['bank_ids', 'in', bids)]``, that returns a
  list of (res.partner) pids
- 1 on res_partner, with a domain ``[('id', 'in', pids)]``

When the _auto_join attribute is True,  it will perform a select on res_partner
as well as on res_partner_bank.

- the relational table will be accessed through an alias: ``'"res_partner_bank"
  as res_partner__bank_ids``
- the relational table will have a join condition on the main table:
  ``res_partner__bank_ids."partner_id"=res_partner."id"``
- the condition will be written on the relational table:
  ``res_partner__bank_ids."name" = 'foo'``

This job is performed in expression.parse(). For leafs containing a path, it
checks whether the first item of the path is a *many2one* or *one2many* field
with the ``auto_join`` attribute set. If set, it adds a join query and recursively
analyzes the remaining of the leaf, going back to the normal behavior when
not reaching an ``_auto_join`` field. The sql condition created from the leaf
will be updated to take into account the table aliases.

Chaining _auto_join allows to reduce the number of queries performed, and to
avoid having too long ``('id', 'in', ids)`` replacement leafs in domains.
However, severe limitations exist on this feature that limits its current use as
of version 7.0. **This feature is therefore considered as experimental, and used
to speedup some precise bottlenecks in OpenERP**.

List of known issues and limitations:

- using _auto_join bypasses the business logic; no name search is performed, only
  direct matches between ids using join conditions
- ir.rules are not taken into account when performing the _auto_join. 
- support of active_test is not asserted
- support of translation is not asserted
- support of _auto_join leading to function fields

Typical use in OpenERP 7.0:

- in mail module: notification_ids field on mail_message, allowing to speedup
  the display of the various mailboxes
- in mail module: message_ids field on mail_thread, allowing to speedup the
  display of needaction counters and documents having unread messages
