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

*Subscribe to the* `project's mailing list (name: Connectors)`_

*Learn how to* :ref:`contribute`

*************
Core Features
*************

* **100% Open Source** (`AGPL version 3`_): the full `source code is available
  on GitHub`_
* Not only designed to connect Odoo with e-commerce backends,
  rather it is **adaptable** to connect Odoo with any type of service.
* **Robust for high volumetries** and **easy to monitor** thanks to a :ref:`jobs-queue`.
* A flexible set of building blocks, it does not force to a certain
  implementation but leaves the final choice to the
  developer on how to use the proposed pieces.
* See a :ref:`code-overview` with examples of code

.. _Odoo: http://www.odoo.com
.. _Camptocamp: http://www.camptocamp.com
.. _Akretion: http://www.akretion.com
.. _Acsone: http://www.acsone.eu
.. _`source code is available on GitHub`: https://github.com/OCA/connector
.. _`AGPL version 3`: http://www.gnu.org/licenses/agpl-3.0.html
.. _`project's mailing list (name: Connectors)`: https://odoo-community.org/groups

*********************************
Connectors based on the framework
*********************************

* `Magento Connector <http://www.odoo-magento-connector.com>`_
* `Prestashop Connector <https://github.com/OCA/connector-prestashop>`_
* `solerp (Solr Connector) <https://github.com/akretion/solerp>`_
* `Odoo Multi Company <http://www.openerp.net.cn/new-intercompany-process-module/>`_
* `CMIS <https://github.com/OCA/connector-cmis>`_
* `Odoo Asynchronous import module <https://github.com/OCA/connector-interfaces/tree/8.0/base_import_async>`_
* `Salesforce Connector <https://github.com/OCA/connector-salesforce>`_
* `Google Spreadsheet Connector <https://github.com/akretion/connector-google-spreadsheet>`_
* `WooCommerce Connector <https://github.com/OCA/connector-woocommerce>`_
* Develop easily and rapidly your own connector based on this powerful
  framework and list your project on this page! Examples:

  * E-Commerce: Odoo OsCommerce connector, Odoo Drupal Commerce connector, Odoo Spree connector, Odoo Ebay connector, Odoo Amazon connector…
  * CMS: Odoo Wordpress connector…
  * CRM: Odoo SugarCRM connector, Odoo Zabbix connector…
  * Project Management: Odoo Redmine connector…
  * Ticketing: Odoo Request Tracker connector, Odoo GLPI connector…

********
Overview
********

.. raw:: html

    <div style="margin-top:10px;">
         <iframe src="http://www.slideshare.net/slideshow/embed_code/24048994?rel=0" width="427" height="356" frameborder="0" marginwidth="0" marginheight="0" scrolling="no" style="border:1px solid #CCC;border-width:1px 1px 0;margin-bottom:5px" allowfullscreen> </iframe> <div style="margin-bottom:5px"> <strong> <a href="https://fr.slideshare.net/openobject/ecommerce-the-new-magento-open-erp-connector-a-generic-connector-to-any-apps-luc-maurer-guewen-baconnier-camptocamp" title="E-commerce: the new Magento - Odoo Connector: a generic connector to any apps. Luc Maurer &amp; Guewen Baconnier, Camptocamp" target="_blank">E-commerce: the new Magento - Odoo Connector: a generic connector to any apps. Luc Maurer &amp; Guewen Baconnier, Camptocamp (OpenERP Days 2013)</a> </strong> from <strong><a href="http://www.slideshare.net/openobject" target="_blank">OpenERP.tv</a></strong> </div>
    </div>

**************************
Top financial contributors
**************************

.. image:: _static/img/LogicSupply_Orange_260x80_transparent.png
   :alt: Logic Supply
   :target: http://www.logicsupply.com

.. image:: _static/img/logo-debonix.jpg
   :alt: Debonix
   :target: http://www.debonix.fr

|
*See all the project's* :ref:`financial-contributors`.

*******
Project
*******

.. toctree::
   :maxdepth: 1

   project/contribute
   project/contributors
   project/license
   project/changes
   project/roadmap

*****************
Developer's guide
*****************

.. toctree::
   :maxdepth: 2

   guides/code_overview.rst
   guides/concepts.rst
   guides/bootstrap_connector.rst
   guides/jobrunner.rst
   guides/multiprocessing.rst

API Reference
=============

.. toctree::
   :maxdepth: 1

   api/api_connector.rst
   api/api_session.rst
   api/api_backend.rst
   api/api_event.rst
   api/api_binder.rst
   api/api_mapper.rst
   api/api_synchronizer.rst
   api/api_backend_adapter.rst
   api/api_queue.rst
   api/api_exception.rst
   api/api_channels.rst
   api/api_runner.rst

******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
