.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

====================
Accounting Documents
====================

This module is intended to be used by many localizations (like Argentina one)

We add many functionalities as:

* New model "account.document.type"
* New fields on "account.move": "document_number" and "document_type_id".

    * This two fields are going to be computed from other models like invoices, payments, etc.
    * We decided to use this indepenent number for different reasons:

        1. We do not touch much of odoo (you can install/uninstall this module)
        2. We don't have any constraint to what we need (for eg. we can have two journal entries with same document numbers)
        3. For eg, in argentina, the document number for a Invoice is '0001-00000001' and you can have many invoices with same document number (for eg. for purchases and for eg. for different document types)

* Modification on reports to show or not taxes regardin document letter

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/account-financial-tools/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* |company| |icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.
