:banner: banners/installing_odoo.jpg

.. _setup/update:

=============================
Updating an Odoo installation
=============================

Introduction
============

In order to benefit from the latest improvements, security fixes, bug corrections and
performance boosts, you may need to update your Odoo installation from time to time.

This guide only applies when are using Odoo on your own hosting infrastructure.
If you are using one of the Odoo Cloud solutions, updates are automatically performed for you.

The terminology surrounding software updates is often confusing, so here are some preliminary
definitions:

Updating (an Odoo installation)
  Refers to the process of obtaining the latest revision of the source code for
  your current Odoo Edition. For example, updating your Odoo Enterprise 12.0 to the
  latest revision.
  This does not directly cause any change to the contents of your Odoo database, and
  can be undone by reinstalling the previous revision of the source code.

Upgrading (an Odoo database)
  Refers to a complex data processing operation where the structure and contents of your
  database is permanently altered to make it compatible with a new release of Odoo.
  This operation is irreversible and typically accomplished via Odoo's
  `database upgrade service <https://upgrade.odoo.com>`_, when you decide to
  switch to a newer release of Odoo.
  Historically, this process has also been known as a "migration" because it involves moving data
  around inside the database, even though the database may end up at the same physical location
  after the upgrade.

This page describes the typical steps needed to *update* an Odoo installation to the latest
version. If you'd like more information about upgrading a database, please visit the
`Odoo Upgrade page <https://upgrade.odoo.com>`_ instead.


In a nutshell
=============

Updating Odoo is accomplished by simply reinstalling the latest version of your Odoo
Edition on top of your current installation. This will preserve your data without any alteration,
as long as you do not uninstall PostgreSQL (the database engine that comes with Odoo).

The main reference for updating is logically our :ref:`installation guide <setup/install>`,
which explains the common installation methods.

Updating is also most appropriately accomplished by the person who deployed Odoo initially,
because the procedure is very similar.

.. note:: We always recommend to download a complete new up-to-date Odoo version, rather than
          manually applying patches, such as the security patches that come with Security
          Advisories.
          The patches are mainly provided for installations that are heavily customized, or for
          technical personnel who prefer to apply minimal changes temporarily while testing a
          complete update.


Step 1: Download an updated Odoo version
========================================

The central download page is https://www.odoo.com/page/download. If you see a "Buy" link for the
Odoo Enterprise download, make sure you are logged into Odoo.com with the same login that is
linked to your Odoo Enterprise subscription.

Alternatively, you can use the unique download link that was included with your Odoo Enterprise
purchase confirmation email.

.. note:: Downloading an updated version is not necessary if you installed via Github (see below)


Step 2: Make a backup of your database
======================================

The update procedure is quite safe and should not alter you data. However it's always best to take
a full database backup before performing any change on your installation, and to store it somewhere
safe, on a different computer.

If you have not disabled the database manager screen (see :ref:`here <security>` why you should), you
can use it (link at bottom of your database selection screen) to download a backup of your
database(s). If you disabled it, use the same procedure than for your usual backups.


Step 3: Install the updated version
===================================

Choose the method that matches your current installation:


Packaged Installers
-------------------

If you installed Odoo with an installation package downloaded on our website (the recommended method),
updating is very simple.
All you have to do is download the installation package corresponding to your system (see step #1)
and install it on your server. They are updated daily and include the latest security fixes.
Usually, you can simply double-click the package to install it on top of the current installation.
After installing the package, be sure to restart the Odoo service or reboot your server,
and you're all set.

Source Install (Tarball)
------------------------
If you have originally installed Odoo with the "tarball" version (source code archive), you have
to replace the installation directory with a newer version. First download the latest tarball
from Odoo.com. They are updated daily and include the latest security fixes (see step #1)
After downloading the package, extract it to a temporary location on your server.

You will get a folder labelled with the version of the source code, for example "odoo-12.0+e.20180719",
that contains a folder "odoo.egg-info" and the actual source code folder named "odoo" (for Odoo 10
and later) or "openerp" for older versions.
You can ignore the odoo.egg-info folder. Locate the folder where your current installation is deployed,
and replace it with the newer "odoo" or "openerp" folder that was in the archive you just extracted.

Be sure to match the folder layout, for example the new "addons" folder included in the source code
should end up exactly at the same path it was before. Next, watch out for any specific configuration
files that you may have manually copied or modified in the old folder, and copy them over to the
new folder.
Finally, restart the Odoo service or reboot the machine, and you are all set.

Source Install (Github)
-----------------------
If you have originally installed Odoo with a full Github clone of the official repositories, the
update procedure requires you to pull the latest source code via git.
Change into the directory for each repository (the main Odoo repository, and the Enterprise
repository), and run the following commands::

     git fetch
     git rebase --autostash

The last command may encounter source code conflicts if you had edited the Odoo source code locally.
The error message will give you the list of files with conflicts, and you will need to resolve
the conflicts manually, by editing them and deciding which part of the code to keep.

Alternatively, if you prefer to simply discard the conflicting changes and restore the official
version, you can use the following command::

     git reset --hard

Finally, restart the Odoo service or reboot the machine, and you should be done.


Docker
------

Please refer to our `Docker image documentation <https://hub.docker.com/_/odoo/>`_ for
specific update instructions.