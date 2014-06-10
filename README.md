Odoo
----

Odoo is a suite of web based open source business apps.  More info at http://www.odoo.com

The easiest way to play with it is the <a href="https://www.odoo.com/page/start">Odoo free trial</a>, email registration is NOT required, use the "skip this step" link on the registration page to skip it.


Getting started with Odoo development
--------------------------------------

If you are a developer type the following command at your terminal [1]:

    wget -O- https://raw.githubusercontent.com/odoo/odoo/master/odoo.py | python

Then follow <a href="https://doc.openerp.com/trunk/server/howto/howto_website/">the developer tutorial</a>

[1] You may want to check the content of the <a href="https://raw.githubusercontent.com/odoo/odoo/master/odoo.py">odoo.py file</a> before executing it.


Packages, tarballs and installers
---------------------------------

* Debian packages

    Add this apt repository to your /etc/apt/sources.list file

        deb http://nightly.openerp.com/8.0/deb/ ./

    Then type:

        $ sudo apt-get update
        $ sudo apt-get install odoo

* <a href="http://nightly.openerp.com/">Source tarballs</a>

* <a href="http://nightly.openerp.com/">Windows installer</a>

* <a href="http://nightly.openerp.com/">RPM package</a>


For Odoo employees
------------------

To add the odoo-dev remote use this command:

    $ ./odoo.py setup_git_dev

To fetch odoo merge pull requests refs use this command:

    $ ./odoo.py setup_git_review

