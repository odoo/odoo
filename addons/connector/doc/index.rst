.. Connectors documentation master file, created by
   sphinx-quickstart on Mon Feb  4 11:35:44 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

##############
Odoo Connector
##############

Odoo Connector is a powerful framework to develop any kind of
bi-directional connector between `Odoo`_ (Open Source ERP) and any other
software or service.

This Odoo add-on has a modular and generic core, with the
ability to be extended with additional modules for new features or
customizations.

The development of Odoo Connector has been started by `Camptocamp`_ and is now
maintained by `Camptocamp`_, `Akretion`_, `Acsone`_ and several :ref:`contributors`.

It got a major overhaul in 2017 (Odoo 10.0). A :ref:`migration-guide` is
available.

*Subscribe to the* `project's mailing list (name: Connectors)`_

*Learn how to* :ref:`contribute`

*************
Core Features
*************

* **100% Open Source** (`LGPL version 3`_): the full `source code is available
  on GitHub`_
* Not only designed to connect Odoo with e-commerce backends,
  rather it is **adaptable** to connect Odoo with any type of service.
* **Robust for high volumetries** and **easy to monitor** thanks to a :ref:`jobs-queue`.
* A flexible set of building blocks, it does not force to a certain
  implementation but leaves the final choice to the
  developer on how to use the proposed pieces.
* See a :ref:`code-overview` with examples of code

.. _Odoo: https://www.odoo.com
.. _Camptocamp: https://www.camptocamp.com
.. _Akretion: http://www.akretion.com
.. _Acsone: https://www.acsone.eu
.. _`source code is available on GitHub`: https://github.com/OCA/connector
.. _`LGPL version 3`: https://www.gnu.org/licenses/lgpl-3.0.html
.. _`project's mailing list (name: Connectors)`: https://odoo-community.org/groups

*****************
Developer's guide
*****************

.. toctree::
   :maxdepth: 2

   guides/migration_guide.rst
   guides/code_overview.rst
   guides/concepts.rst
   guides/bootstrap_connector.rst
   guides/jobrunner.rst

API Reference
=============

.. toctree::
   :maxdepth: 1

   api/api_components.rst
   api/api_backend.rst
   api/api_event.rst
   api/api_queue.rst
   api/api_exception.rst
   api/api_channels.rst

*******
Project
*******

.. toctree::
   :maxdepth: 1

   project/contribute
   project/contributors
   project/license
   project/roadmap

*********************************
Connectors based on the framework
*********************************

* `Magento Connector <http://www.odoo-magento-connector.com>`_
* `Prestashop Connector <https://github.com/OCA/connector-prestashop>`_
* `Search Engine Connector <https://github.com/akretion/connector-search-engine>`_
* `CMIS <https://github.com/OCA/connector-cmis>`_
* `Odoo Asynchronous import module <https://github.com/OCA/connector-interfaces/tree/8.0/base_import_async>`_
* `Salesforce Connector <https://github.com/OCA/connector-salesforce>`_
* `JIRA Connector <https://github.com/camptocamp/connector-jira>`_
* `Google Spreadsheet Connector <https://github.com/akretion/connector-google-spreadsheet>`_
* `Connector Exchange <https://github.com/camptocamp/connector-exchange/tree/10.0>`_
* `Infor Connector <https://github.com/OCA/connector-infor>`_
* `Voicent Connector <https://github.com/ursais/osi-addons>`_
* Develop easily and rapidly your own connector based on this powerful
  framework and list your project on this page! Examples:

  * E-Commerce: Odoo OsCommerce connector, Odoo Drupal Commerce connector, Odoo Spree connector, Odoo Ebay connector, Odoo Amazon connector…
  * CMS: Odoo Wordpress connector…
  * CRM: Odoo SugarCRM connector, Odoo Zabbix connector…
  * Project Management: Odoo Redmine connector…
  * Ticketing: Odoo Request Tracker connector, Odoo GLPI connector…


*****
Talks
*****

* `A jobs queue for processing tasks asynchronously. Leonardo Pistone & Guewen Baconnier (2015) <https://fr.slideshare.net/camptocamp/a-jobs-queue-for-processing-tasks-asynchronously>`_
* `E-commerce: the new Magento - OpenERP Connector: a generic connector to any apps. Luc Maurer & Guewen Baconnier, Camptocamp (2013) <https://fr.slideshare.net/openobject/ecommerce-the-new-magento-open-erp-connector-a-generic-connector-to-any-apps-luc-maurer-guewen-baconnier-camptocamp>`_

******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
