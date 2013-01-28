.. _security:

==================================
Security in OpenERP: users, groups
==================================

Users and user roles are critical points concerning internal security in
OpenERP. OpenERP provides several security mechanisms concerning user roles,
all implemented in the OpenERP Server. They are implemented in the lowest
server level, which is the ORM engine. OpenERP distinguishes three different
concepts:

 - user: a person identified by its login and password. Note that all employees
   of a company are not necessarily OpenERP users; an user is somebody who
   accesses the application.
 - group: a group of users that has some access rights. A group gives its
   access rights to the users that belong to the group. Ex: Sales Manager,
   Accountant, etc.
 - security rule: a rule that defines the access rights a given group grants
   to its users. Security rules are attached to a given resource, for example
   the Invoice model.

Security rules are attached to groups. Users are assigned to several groups.
This gives users the rights that are attached to their groups. Therefore 
controlling user roles is done by managing user groups and adding or modifying 
security rules attached to those groups.

Users
======

Users represent physical persons using OpenERP. They are identified with
a login and a password,they use OpenERP, they can edit their own preferences, ...
By default, a user has no access right. The more we assign groups to the user,
the more he or she gets rights to perform some actions. A user may belong 
to several groups.

User groups
===========

The groups determine the access rights to the different resources. A user
may belong to several groups. If he belongs to several groups, we always 
use the group with the highest rights for a selected resource. A group 
can inherit all the rights from another group

Figure 3 shows how group membership is displayed in the web client. The user
belongs to Sales / Manager, Accounting / Manager, Administration / Access Rights,
Administration / Configuration and Human Resources / Employee groups. Those 
groups define the user access rights.

Figure 3: Example of group membership for a given user

Rights
======

Security rules are attached to groups. You can assign several security 
rules at the group level, each rule being of one of the following types :

 - access rights are global rights on an object,
 - record rules are records access filters,
 - fields access right,
 - workflow transition rules are operations rights.
 
You can also define rules that are global, i.e. they are applied to all
users, indiscriminately of the groups they belong to. For example, the
multi-company rules are global; a user can only see invoices of the companies 
he or she belongs to.


Concerning configuration, it is difficult to have default generic configurations 
that suit all applications. Therefore, like SAP, OpenERP is by default 
pre-configured with best-practices.

Access rights
=============

Access rights are rules that define the access a user can have on a particular
object . Those global rights are defined per document type or model. Rights 
follow the CRUD model: create, read (search), update (write), delete. For 
example, you can define rules on invoice creation. By default, adding a 
right to an object gives the right to all records of that specific object.

Figure 4 shows some of the access rights of the Accounting / Accountant group.
The user has some read access rights on some objects.

Figure 4: Access rights for some objects.

Record rules
++++++++++++

When accessing an object, records are filtered based on record rules. Record 
rules or access filters are therefore filters that limits records of an 
object a group can access. A record rule is a condition that each record 
must satisfy to be created, read, updated (written) or deleted. Records 
that do not meet the constraints are filtered.

For example, you can create a rule to limit a group in such a way that 
users of that group will see business opportunities in which he or she is 
flagged as the salesman. The rule can be salesman = connected_user. With 
that rule, only records respecting the rule will be displayed.


Field access rights
+++++++++++++++++++

.. versionadded:: 7.0

OpenERP now supports real access control at the field level, not just on the view side.
Previously it was already possible to set a ``groups`` attribute on a ``<field>`` element
(or in fact most view elements), but with cosmetics effects only: the element was made
invisible on the client side, while still perfectly available for read/write access at
the RPC level.

As of OpenERP 7.0 the existing behavior is preserved on the view level, but a new ``groups``
attribute is available on all model fields, introducing a model-level access control on
each field. The syntax is the same as for the view-level attribute::

    _columns = {
        'secret_key': fields.char('Secret Key', groups="base.group_erp_manager,base.group_system")
     }

There is a major difference with the view-level ``groups`` attribute: restricting
the access at the model level really means that the field will be completely unavailable
for users who do not belong to the authorized groups:

* Restricted fields will be **completely removed** from all related views, not just
  hidden. This is important to keep in mind because it means the field value will not be
  available at all on the client side, and thus unavailable e.g. for ``on_change`` calls.
* Restricted fields will not be returned as part of a call to
  :meth:`~openerp.osv.orm.fields_get` or :meth:`~openerp.osv.orm.fields_view_get`
  This is in order to avoid them appearing in the list of fields available for
  advanced search filters, for example. This does not prevent getting the list of
  a model's fields by querying ``ir.model.fields`` directly, which is fine. 
* Any attempt to read or write directly the value of the restricted fields will result
  in an ``AccessError`` exception.
* As a consequence of the previous item, restricted fields will not be available for
  use within search filters (domains) or anything that would require read or write access.
* It is quite possible to set ``groups`` attributes for the same field both at the model
  and view level, even with different values. Both will carry their effect, with the
  model-level restriction taking precedence and removing the field completely in case of
  restriction.

.. note:: The tests related to this feature are in ``openerp/tests/test_acl.py``.
 
Workflow transition rules
+++++++++++++++++++++++++

Workflow transition rules are rules that restrict some operations to certain 
groups. Those rules handle rights to go from one step to another one in the 
workflow. For example, you can limit the right to validate an invoice, i.e. 
going from a draft action to a validated action.

Menu accesses
=============

In OpenERP, granting access to menus can be done using user groups. A menu 
that is not granted to any group is accessible to every user. It is possible 
in the administration panel to define the groups that can access a given menu.

However, one should note that using groups to hide or give access to menus 
is more within the filed of ergonomics or usability than within the field 
of security. It is a best practice putting rules on documents instead of 
putting groups on menu. For example, hiding invoices can be done by modifying 
the record rule on the invoice object, and it is more efficient and safer 
than hiding menus related to invoices.

Views customization
===================

Customizing views based on groups is possible in OpenERP. You can put rules 
to display some fields based on group rules. However, as with menu accesses 
customization, this option should not be considered for security concerns. 
This way of customizing views belongs more to usability.

Administration
==============

When installing your particular instance of OpenERP, a specific first user 
is installed by default. This first user is the Super User or administrator. 
The administrator is by default added access rights to every existing groups, 
as well as to every groups created during a new module installation. He also 
has access to a specific administration interface accessible via the administration 
menu, allowing the administration of OpenERP.

The administrator has rights to manage groups; he can add, create, modify 
or remove groups. He may also modify links between users and groups, such 
as adding or removing users. He also manages access rights. With those 
privileges, the administrator can therefore precisely define security 
accesses of every users of OpenERP.

There are user groups that are between normal groups and the super user. 
Those groups are Administration / Configuration and Administration / Access Rights. 
It gives to the users of those groups the necessary rights to configure access rights.

