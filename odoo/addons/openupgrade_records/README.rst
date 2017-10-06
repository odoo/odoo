.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===============================
OpenUpgrade Database Comparison
===============================

This module provides the tool to generate the database analysis files that indicate how the Odoo data model and module data have changed between two versions of Odoo. Database analysis files for the core modules are included in the OpenUpgrade distribution so as a migration script developer you will not usually need to use this tool yourself. If you do need to run your analysis of a custom set of modules, please refer to the documentation here: https://doc.therp.nl/openupgrade/analysis.html

Installation
============

This module has a python dependency on openerp-client-lib. You need to make this module available in your Python environment, for instance by installing it with the pip tool.

Known issues / Roadmap
======================

* scripts/compare_noupdate_xml_records.py should be integrated in the analysis process (#590)
* Log removed modules in the module that owned them (#468)
* Detect renamed many2many tables (#213)

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/openupgrade/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Stefan Rijnhart <stefan@opener.amsterdam>
* Holger Brunn <hbrunn@therp.nl>
* Pedro M. Baeza <pedro.baeza@gmail.com>
* Ferdinand Gassauer <gass@cc-l-12.chircar.at>
* Florent Xicluna <florent.xicluna@gmail.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
