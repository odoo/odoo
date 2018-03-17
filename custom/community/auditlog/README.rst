.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

=================================
Audit Log - Track user operations
=================================

This module allows the administrator to log user operations performed on data
models such as ``create``, ``read``, ``write`` and ``delete``.

Usage
=====

Go to `Settings / Technical / Audit / Rules` to subscribe rules. A rule defines
which operations to log for a given data model.

.. image:: /auditlog/static/description/rule.png

Then, check logs in the `Settings / Technical / Audit / Logs` menu. You can
group them by user sessions, date, data model or HTTP requests:

.. image:: /auditlog/static/description/logs.png

Get the details:

.. image:: /auditlog/static/description/log.png

A scheduled action exists to delete logs older than 6 months (180 days)
automatically but is not enabled by default.
To activate it and/or change the delay, go to the
`Configuration / Technical / Automation / Scheduled Actions` menu and edit the
`Auto-vacuum audit logs` entry:

.. image:: /auditlog/static/description/autovacuum.png

Known issues / Roadmap
======================

 * log only operations triggered by some users (currently it logs all users)


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/server-tools/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/server-tools/issues/new?body=module:%20auditlog%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


Credits
=======

Contributors
------------

* Sebastien Alix <sebastien.alix@osiell.com>
* Holger Brunn <hbrunn@therp.nl>
* Holden Rehg <holdenrehg@gmail.com>

Images
------

* Icon: built with different icons from the `Oxygen theme <https://en.wikipedia.org/wiki/Oxygen_Project>`_ (LGPL)

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
