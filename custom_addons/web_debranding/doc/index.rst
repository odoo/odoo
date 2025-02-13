====================
 Backend debranding
====================

Installation
============

* `Install <https://odoo-development.readthedocs.io/en/latest/odoo/usage/install-module.html>`__ this module in a usual way

Configuration
=============

By default the module replaces ``Odoo`` to ``紫色💃团子``.

* Switch to Developer mode
* Open ``[[ General Settings ]] >> Technical >> Parameters >> System Parameters`` and modify:

  * ``web_debranding.new_title`` (put space in *Value field* if you don't need Brand in Title)
  * ``web_debranding.new_name`` (your Brand)
  * ``web_debranding.new_website`` (your website)
  * ``web_debranding.new_documentation_website`` (website with documentation instead of official one)
  * ``web_debranding.favicon_url``
  * ``web_debranding.send_publisher_warranty_url`` - set 0 to disable server requests to odoo.com and 1 otherwise (useful for enterprise contractors). Works only for non-enterprise versions of odoo, check `note <https://www.odoo.com/apps/modules/17.0/web_debranding/#enterprise-users-notice>`__ below.

Further debranding
==================

* Install `portal_debranding <https://apps.odoo.com/apps/modules/17.0/portal_debranding/>`__ if module *Portal* is already installed in your system
* Install `website_debranding <https://apps.odoo.com/apps/modules/17.0/website_debranding/>`__ if module *Website Builder* is already installed in your system
* Install `pos_debranding <https://apps.odoo.com/apps/modules/17.0/pos_debranding/>`__ if module *POS* is already installed in your system
* Delete *Odoo.com Accounts* record at *Settings >> Users & Companies >> OAuth Providers* if module ``OAuth2 Authentication`` has been already installed in your system
* Database switcher ``/web/database/manager``: edit *addons/web/static/src/public/database_manager.qweb.html* file
* Favicon: open ``[[ Settings ]] >> Users & Companies >> Companies`` and change **Company Favicon**
* Bot's Avatar: open Users menu, apply filter *Inactive Users*, change avatar of the bot to a custom one
* Emails: use OCA's `Mail Debrand <https://apps.odoo.com/apps/modules/17.0/mail_debrand/>`__ module

Auto-debrand new databases
==========================

To automatically install this module for every new databases set ``'auto_install': True`` in ``web_debranding/__manifest__.py`` file.

Usage
=====

* Open *Backend*
* Perform usual workflow

RESULT: references to `Odoo <https://www.odoo.com/>`__ are hidden as much as possible (let us know if you found one)..

Examples
========

* Search a random string at the menu ``[[ Settings ]] >> Users & Companies >> Companies``

    Create and manage the companies that will be managed by **Odoo** from here. Shops or subsidiaries can be created and maintained from here.

* Try to delete archived Bot user (login: ``__system__``) via menu ``[[ Settings ]] >> Users & Copanies >> Users``

    You can not remove the admin user as it is used internally for resources created by *Odoo** (updates, module installation, ...).

* When you create new company it shows placeholder for field **Website**

    e.g. www.odoo.com

* Install `website_twitter` module and open menu ``[[ Settings ]] >> General Settings >> Website``.

  Name: **Odoo** Twitter Integration

* Open menu ``[[ Discuss ]] >> CHANNELS >> #general``

  * Send ``/help`` to the chat and **OdooBot** will send you some text

* Open two browser tabs with Odoo. Then logout in one of it. Open any menu in another one.

    Your **Odoo** session expired. The current page is about to be refreshed.

* Install `sale_management` module and open menu ``[[ Settings ]] >> Sales``.

  * RESULT: the Enterprise features are hidden
