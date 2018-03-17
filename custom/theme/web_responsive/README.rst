.. image:: https://img.shields.io/badge/license-LGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
   :alt: License: LGPL-3

==============
Web Responsive
==============

This module provides a mobile compliant interface for Odoo Community web.

Features:

 * New navigation with an App drawer
 * Keyboard shortcuts for easier navigation


Installation
============

Configuration
=============

Usage
=====

Keyboard Shortcuts
------------------

The following keyboard shortcuts are implemented:

* Toggle App Drawer - `ActionKey <https://en.wikipedia.org/wiki/Access_key#Access_in_different_browsers>` + ``A``
* Navigate Apps Drawer - Arrow Keys
* Type to select App Links
* ``esc`` to close App Drawer

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/162/10.0

Known issues / Roadmap
======================

Note: Data added to the footer ``support_branding`` is not shown while using
this module.

* Provide full menu search feature instead of just App search
* Drag drawer from left to open in mobile
* Figure out how to test focus on hidden elements for keyboard nav tests
* If you resize the window, body gets a wrong ``overflow: auto`` css property
  and you need to refresh your view or open/close the app drawer to fix that.
* Override LESS styling to allow for responsive widget layouts
* Adding ``oe_main_menu_navbar`` ID to the top navigation bar triggers some
  great styles, but also `JavaScript that causes issues on mobile
  <https://github.com/OCA/web/pull/446#issuecomment-254827880>`_

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/web/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.


Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Dave Lasley <dave@laslabs.com>
* Jairo Llopis <jairo.llopis@tecnativa.com>
* Dennis Sluijk <d.sluijk@onestein.nl>

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
