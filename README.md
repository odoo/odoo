About Odoo
==========

Odoo is a suite of open source Business apps.  More info at http://www.odoo.com

Evaluating Odoo
---------------

The easiest way to test Odoo is the free trial, NO email registration is
required, select "skip this step" to skip it.

    https://www.odoo.com/page/start


Getting starting with Odoo developement
---------------------------------------

If you are a developer type the following command at your terminal:

    wget -O- https://raw.githubusercontent.com/odoo/odoo/master/odoo.py | python

Then follow the tutorial here:

    https://doc.openerp.com/trunk/server/howto/howto_website/

If you are an Odoo employee type the following to add the odoo-dev remote

    $ cd odoo; ./odoo.py setup_git_dev


Packages, tarballs and installers
---------------------------------

* Debian packages

    Add this apt repository to your /etc/apt/sources.list file

        deb http://nightly.openerp.com/8.0/deb/ ./

    Then type:

        $ sudo apt-get update
        $ sudo apt-get install odoo

* Source tarballs http://nightly.openerp.com/
* Windows installer http://nightly.openerp.com/
* RPM package http://nightly.openerp.com/

