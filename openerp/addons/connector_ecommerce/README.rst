.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License

Connector for E-Commerce
========================

This modules aims to be a common layer for the connectors dealing with
e-commerce.

It sits on top of the `connector`_ framework and is used by the
e-commerce connectors, like `magentoerpconnect`_ or
`prestashoperpconnect`_.

That's a technical module, which include amongst other things:

Events

  On which the connectors can subscribe consumers
  (tracking number added, invoice paid, picking sent, ...)

ConnectorUnit

  A piece of code which allows to play all the ``onchanges`` required
  when we create a sales order.

  Another one which allows to add special lines in imported sales orders
  such as Shipping fees, Cash on Delivery or Discounts.

Data Model

  Add structures shared for e-commerce connectors

.. _`connector`: http://odoo-connector.com
.. _`magentoerpconnect`: http://odoo-magento-connector.com
.. _`prestashoperpconnect`: https://github.com/OCA/connector-prestashop

Installation
============

This module is a dependency for more advanced connectors. It does
nothing on its own and there is no reason to install it alone.


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/connector-ecommerce/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/connector-ecommerce/issues/new?body=module:%20connector_ecommerce%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


Credits
=======

Contributors
------------

See `contributors' list`_

.. _contributors' list: ./AUTHORS

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization
whose mission is to support the collaborative development of Odoo
features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
