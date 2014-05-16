About Odoo
==========

Odoo is suite of OpenSource Business apps. More info at:

    http://www.odoo.com

Odoo git workflow
=================

    https://github.com/odoo/odoo/blob/master/doc/git.rst

Installation
============

System Requirements
-------------------

The dependencies are listed in setup.py

For Luxembourg localization, you also need:

 pdftk (http://www.pdflabs.com/tools/pdftk-the-pdf-toolkit/)

Debian/Ubuntu
-------------

Add the the apt repository

    deb http://nightly.openerp.com/6.1/deb/ ./

in your source.list and type:

    $ sudo apt-get update
    $ sudo apt-get install openerp

Or download the deb file and type:

    $ sudo dpkg -i <openerp-deb-filename>
    $ sudo apt-get install install -f

RedHat, Fedora, CentOS
----------------------

Install the required dependencies:

    $ yum install python
    $ easy_install pip
    $ pip install .....

Install the openerp rpm

    $ rpm -i openerp-VERSION.rpm

Windows
-------

    Check the notes in setup.py

Setting up your database
------------------------

Point your browser to http://localhost:8069/ and click "Manage Databases", the
default master password is "admin".
