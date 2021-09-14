[![Build Status](https://runbot.odoo.com/runbot/badge/flat/1/master.svg)](https://runbot.odoo.com/runbot)
[![Tech Doc](https://img.shields.io/badge/master-docs-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/documentation/16.0)
[![Help](https://img.shields.io/badge/master-help-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/forum/help-1)
[![Nightly Builds](https://img.shields.io/badge/master-nightly-875A7B.svg?style=flat&colorA=8F8F8F)](https://nightly.odoo.com/)

# Odoo

Odoo is a suite of web based open source business apps.

The main Odoo Apps include an <a href="https://www.odoo.com/page/crm">Open Source CRM</a>,
<a href="https://www.odoo.com/app/website">Website Builder</a>,
<a href="https://www.odoo.com/app/ecommerce">eCommerce</a>,
<a href="https://www.odoo.com/app/inventory">Warehouse Management</a>,
<a href="https://www.odoo.com/app/project">Project Management</a>,
<a href="https://www.odoo.com/app/accounting">Billing &amp; Accounting</a>,
<a href="https://www.odoo.com/app/point-of-sale-shop">Point of Sale</a>,
<a href="https://www.odoo.com/app/employees">Human Resources</a>,
<a href="https://www.odoo.com/app/social-marketing">Marketing</a>,
<a href="https://www.odoo.com/app/manufacturing">Manufacturing</a>,
<a href="https://www.odoo.com/">...</a>

Odoo Apps can be used as stand-alone applications, but they also integrate seamlessly so you get
a full-featured <a href="https://www.odoo.com">Open Source ERP</a> when you install several Apps.

## Getting started with Odoo

For a standard installation please follow the <a href="https://www.odoo.com/documentation/16.0/administration/install/install.html">Setup instructions</a>
from the documentation.

To learn the software, we recommend the <a href="https://www.odoo.com/slides">Odoo eLearning</a>, or <a href="https://www.odoo.com/page/scale-up-business-game">Scale-up</a>, the <a href="https://www.odoo.com/page/scale-up-business-game">business game</a>. Developers can start with <a href="https://www.odoo.com/documentation/16.0/developer/howtos.html">the developer tutorials</a>

# ⚠️ Updating Python dependencies

Be aware that when working with `pyproject.toml` file you also have to update `pyproject.toml` in our
[odoo-addons-jobrad](https://github.com/jobrad-gmbh/odoo-addons-jobrad) repository.

[`jobrad-gmbh/odoo-addons-jobrad/pyproject.toml`](https://github.com/jobrad-gmbh/odoo-addons-jobrad/blob/develop/pyproject.toml)
is a **superset** of
[`jobrad-gmbh/odoo/pyproject.toml`](https://github.com/jobrad-gmbh/odoo/blob/jobrad-16.0/pyproject.toml) which means
that the group `[tool.poetry.group.odoo.dependencies]` is present in both of the files. This is a consequence of us
versioning projects and their sets of dependencies instead of Python packages. Since we are "gluing" repositories
together, their `pyproject.toml` files have to be in sync.

The process of updating
[`jobrad-gmbh/odoo-addons-jobrad/pyproject.toml`](https://github.com/jobrad-gmbh/odoo-addons-jobrad/blob/develop/pyproject.toml)
has been automated through
[`scripts/python_environment/sync-odoo-deps-in-pyproject-toml.py`](https://github.com/jobrad-gmbh/odoo-addons-jobrad/blob/develop/scripts/python_environment/sync-odoo-deps-in-pyproject-toml.py).
In order to run the script, you need to have Python and Poetry installed. The script updates
`[tool.poetry.group.odoo.dependencies]` group and runs `poetry lock` for you. If you want to see how the new
`pyproject.toml` will look like without actually updating it, you can specify `--dry-run` flag.

For more information, read [this](https://github.com/jobrad-gmbh/odoo-addons-jobrad/blob/develop/docs/development.md).
