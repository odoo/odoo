About Odoo
==========

Odoo is a suite of open source Business apps. More info at http://www.odoo.com

Installation
============

[Setup/migration guide for employees](https://github.com/odoo/odoo/blob/master/doc/git.rst)


Migration from bazaar
=====================

If you have existing bazaar branches and want to move them to a git repository,
there are several options:

* download http://nightly.openerp.com/move-branch.zip and run it with
  `python move-branch.zip -h` (for the help). It should be able to convert
  simple-enough branches for you (even if they have merge commits &al)
* Extract the branch contents as patches and use `git apply` or `git am` to
  rebuild a branch from them
* Replay the branch by hand


System Requirements
-------------------

The dependencies are listed in setup.py


Debian/Ubuntu
-------------

Add the apt repository

    deb http://nightly.openerp.com/7.0/deb/ ./

in your source.list and type:

    $ sudo apt-get update
    $ sudo apt-get install openerp

Or download the deb file and type:

    $ sudo dpkg -i <openerp-deb-filename>
    $ sudo apt-get install -f

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

