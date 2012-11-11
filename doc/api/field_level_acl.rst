Field-level access control
==========================

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
 
.. warning:: At the time of writing the implementation of this feature is partial
             and does not yet restrict read/write RPC access to the field.
             The corresponding test is written already but currently disabled.