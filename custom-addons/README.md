[![Build Status](http://runbot.odoo.com/runbot/badge/flat/7/master.svg)](http://runbot.odoo.com/runbot/repo/git-github-com-odoo-enterprise-7)
[![Tech Doc](http://img.shields.io/badge/14.0-docs-875A7B.svg?style=flat)](http://www.odoo.com/documentation/master)
[![Help](http://img.shields.io/badge/master-help-875A7B.svg?style=flat)](https://www.odoo.com/forum/help-1)
[![Nightly Builds](http://img.shields.io/badge/master-nightly-875A7B.svg?style=flat)](http://nightly.odoo.com/)

Odoo
----

Odoo is a suite of web based open source business apps.

The main Odoo Apps include an <a href="https://www.odoo.com/app/crm">Open Source CRM</a>,
<a href="https://www.odoo.com/app/website">Website Builder</a>,
<a href="https://www.odoo.com/app/ecommerce">eCommerce</a>,
<a href="https://www.odoo.com/app/inventory">Warehouse Management</a>,
<a href="https://www.odoo.com/app/project">Project Management</a>,
<a href="https://www.odoo.com/app/accounting">Billing &amp; Accounting</a>,
<a href="https://www.odoo.com/app/point-of-sale-shop">Point of Sale</a>,
<a href="https://www.odoo.com/app/employees">Human Resources</a>,
<a href="https://www.odoo.com/app/lead-automation">Marketing</a>,
<a href="https://www.odoo.com/app/manufacturing">Manufacturing</a>,
<a href="https://www.odoo.com/app/purchase">Purchase Management</a>,
<a href="https://www.odoo.com/">...</a>

Odoo Apps can be used as stand-alone applications, but they also integrate seamlessly so you get
a full-featured <a href="https://www.odoo.com">Open Source ERP</a> when you install several Apps.

Getting started with Odoo
-------------------------

For a standard installation please follow the <a href="https://www.odoo.com/documentation/17.0/administration/install/install.html">Setup instructions</a>
from the documentation.

If you are a developer you may type the following command at your terminal:

    wget -O- https://raw.githubusercontent.com/odoo/odoo/master/setup/setup_dev.py | python

Then follow <a href="https://www.odoo.com/documentation/17.0/developer/howtos.html">the developer tutorials</a>

For Odoo employees
------------------

To add the odoo-dev remote use this command:

    $ ./setup/setup_dev.py setup_git_dev

To fetch odoo merge pull requests refs use this command:

    $ ./setup/setup_dev.py setup_git_review
