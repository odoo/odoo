[![Build Status](https://runbot.odoo.com/runbot/badge/flat/1/master.svg)](https://runbot.odoo.com/runbot)
[![Tech Doc](https://img.shields.io/badge/master-docs-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/documentation/15.0)
[![Help](https://img.shields.io/badge/master-help-875A7B.svg?style=flat&colorA=8F8F8F)](https://www.odoo.com/forum/help-1)
[![Nightly Builds](https://img.shields.io/badge/master-nightly-875A7B.svg?style=flat&colorA=8F8F8F)](https://nightly.odoo.com/)

Odoo
----

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

Getting started with Odoo
-------------------------

**Table of contents**

<!-- TOC -->

- [1. Setup development environment](#1-setup-development-environment)
- [2. Dependencies](#2-dependencies)
- [3. Work with odoo project everyday](#3-work-with-odoo-project-everyday)

## 1. Setup development environment
### Prerequisites
1. Python

  * Odoo requires Python 3.7 or later to run. Use your preferred package manager (homebrew, macports) to download and install Python 3 [python3](https://formulae.brew.sh/formula/python@3.10) on your machine if it is not already done.


```
brew install python@3.10
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade setuptools
```


2. PostgreSQL
 
  * Odoo uses PostgreSQL as database management system. Use [postgres.app](https://postgresapp.com/) to download and install PostgreSQL (supported version: 10.0 and later).

  * By default, the only user is postgres but Odoo forbids connecting as postgres, so you need to create a new PostgreSQL user:

```
 sudo -u postgres createuser -s $USER
 createdb $USER
```
 * Use [PgAdmin4](https://www.pgadmin.org/download/) to download PostgreSQL Tools.

3. Wkhtmltopdf

* wkhtmltopdf is not installed through pip and must be installed manually  for it to support headers and footers. See our [wiki](https://github.com/odoo/odoo/wiki/Wkhtmltopdf) for more details on the various versions.

```
brew install --cask wkhtmltopdf
```

4. psycopg2-binary 

* To install psycopg2-binary 

```
 pip3 install psycopg2-binary
```
## 2. Dependencies

* Odoo dependencies are listed in the requirements.txt file located at the root of the Odoo community directory.

```
 cd [proj-path]
 pip3 install setuptools wheel
 pip3 install -r requirements.txt
```

## 3. Work with odoo project everyday

```
 cd [proj-path]
 python3 odoo-bin --addons-path=addons -d mydb
```
* To run project  in browser: 

```
http://localhost:8069/
```

 