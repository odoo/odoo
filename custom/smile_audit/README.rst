===========
Audit Trail
===========
.. |badge2| image:: https://img.shields.io/badge/licence-LGPL--3-blue.png
    :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
    :alt: License: LGPL-3.0
.. |badge3| image:: https://img.shields.io/badge/github-Smile_SA%2Fodoo_addons-lightgray.png?logo=github
    :target: https://github.com/Smile-SA/odoo_addons/tree/15.0/smile_audit
    :alt: Smile-SA/odoo_addons

|badge2| |badge3|


This module lets administrator track every user's operation on all the objects of the system (for the moment, only create, write and unlink methods). Each rule for tracking user's operation on data through the Odoo's interface is called audit rule.

Features:

* The administrator creates an audit rule by specifying the name and the module on which the rule will be applied,
* The administrator ticks the operations he wants to follow (creation and/or modification and/or deletion),
* The administrator selects the group of users concerned by the audit.
* A rule can be disabled if the administrator does not want to follow its logs anymore.
* Operations performed by a user will be automatically recorded in the list of logs according to the pre-defined rule.
* The log view contains details about each operation: date, name, the module, the user, old and new values of each modified field, etc.
* The module also allows a history revision of each operation.
* The administrator can delete audit rules but logs can't be deleted.
* Users can view a list of current model logs.

**Table of contents**

.. contents::
   :local:

Usage
=====

To create a new rule:

#. Go to ``Settings > Audit > Rules`` menu.
#. Press the button ``Create``.
#. Insert the name of the rule, the model and the user group. Then check operations you want to audit.

    .. figure:: static/description/create_audit_rules.png
       :alt: Audit rule
       :width: 900px

To show the list of logs and edit a log:

#. Go to ``Settings > Audit > Logs`` menu.

    .. figure:: static/description/show_list_logs.png
       :alt: List of audit logs
       :width: 900px

#. Display the log by clicking on a line to see more details about the operation and changes.

    .. figure:: static/description/display_operation_log.png
       :alt: Line of log
       :width: 900px

To view different versions of the object:

#. Click on the smart button ``History Revision``.

    .. figure:: static/description/display_operation_log2.png
           :alt: Line of log
           :width: 900px

#. Corresponding history:

    .. figure:: static/description/history_revision.png
       :alt: History revision
       :width: 900px

To view logs of displayed model:

#. Select one or multiple lines from the list view.
#. Go to ``Action > View audit logs``.

    .. figure:: static/description/view_audit_logs.png
       :alt: View audit logs
       :width: 900px

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/Smile-SA/odoo_addons/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/Smile-SA/odoo_addons/issues/new?body=module:%20smile_audit%0Aversion:%2012.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

GDPR / EU Privacy
=================

This addons does not collect any data and does not set any browser cookies.

Credits
=======

Contributors
------------

* Corentin POUHET-BRUNERIE
* Majda ELMARIOULI
* Hassan MEZOIR

Maintainer
----------

This module is maintained by Smile SA.

Since 1991 Smile has been a pioneer of technology and also the European expert in open source solutions.

.. image:: https://avatars0.githubusercontent.com/u/572339?s=200&v=4
   :alt: Smile SA
   :target: https://www.smile.eu

This module is part of the `odoo-addons <https://github.com/Smile-SA/odoo_addons>`_ project on GitHub.

You are welcome to contribute.
