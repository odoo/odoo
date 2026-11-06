.. _contribute:

##########
Contribute
##########

We accept with pleasure all type of contributions:

* bug reports
* merge proposals
* ideas
* translations
* ...

Have a look on the :ref:`Magento Connector Developer's Guide
<connectormagento:contribute>` which is more complete, most of the
information is the same.

The GitHub project is: https://github.com/OCA/connector

*****************************
Want to start a new connector
*****************************

If you want to start a new connector based on the framework,
a sane approach is to read this documentation, especially
:ref:`concepts` and :ref:`bootstrap-connector`.

Then, my personal advice is to look at the existing connectors (`Odoo
Magento Connector`_, `Odoo Prestashop Connector`_). You will also probably
need to dive a bit in the framework's code.

If the connector belongs to the e-commerce domain, you may want to reuse the pieces
of the `E-Commerce Connector`_ module.

.. _naming-convention:

Naming conventions
==================

The naming conventions for the new projects are the following:

Name of the project if it is in the OCA:

    connector-xxx

Name of the Odoo module:
    connector_xxx

Example:
    https://github.com/OCA/connector-magento

    ``connector_magento``

Actually, the Magento and Prestashop connectors do not respect this convention
for historical reasons (magentoerpconnect, prestashoperpconnect).
New projects should ideally respect it.

.. _`Odoo Magento Connector`: https://github.com/OCA/connector-magento
.. _`Odoo Prestashop Connector`: https://github.com/OCA/connector-prestashop
.. _`E-Commerce Connector`: https://github.com/OCA/connector-ecommerce

*************************************************
Creating or maintaining a translation of this doc
*************************************************

- Install Odoo, its dependencies, sphinx, sphinx_bootstrap_theme and
  sphinx-intl
- Add `this patch
  <https://bitbucket.org/shimizukawa/sphinx-intl/pull-request/9/>`_
  to sphinx-intl (until merged) to support *fuzzy* translations
- create an empty database with the connector module installed
- ``cd connector/doc``
- rebuild the gettext .pot source catalogs: ``make gettext``
- update the .po translation files from the latest .pot files (here for
  language 'fr'): ``sphinx-intl update -l fr -p _build/locale``
- create or edit the translation in the .po files: ``poedit
  locale/fr/LC_MESSAGES/*.po``
- compile the .po files into .mo files: ``sphinx-intl build``
- build the translated documentation to html: ``make SPHINXOPTS="-Dlanguage=fr"
  html``

The same using a `buildout
<https://bitbucket.org/anybox/public_buildbot_buildouts/src/tip/odoo-connector.cfg>`_::

    $ mkdir buildout && cd buildout
    $ wget https://bitbucket.org/anybox/public_buildbot_buildouts/raw/tip/odoo-connector.cfg -O buildout.cfg
    $ wget https://bitbucket.org/anybox/public_buildbot_buildouts/raw/tip/bootstrap.py
    $ python bootstrap.py
    $ bin/buildout
    $ createdb connectordb
    $ bin/start_odoo -d connectordb --stop-after-init
    $ cd connector/connector/doc/
    $ ../../../bin/sphinx-build -d connectordb -- -b gettext ./ _build/locale/
    $ ../../../bin/sphinx-intl -d connectordb -- update -l fr -p _build/locale/
    $ poedit locale/fr/LC_MESSAGES/*po
    $ ../../../bin/sphinx-intl -d connectordb -- build
    $ ../../../bin/sphinx-build -d connectordb -- -D language=fr -b html ./ _build/html/

Then you can see the result in _build/html/ and submit a Pull Request. Repeat the 5 last steps to update the translation if modified upstream.
