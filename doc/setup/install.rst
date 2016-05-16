:banner: banners/installing_odoo.jpg

.. _setup/install:

===============
Installing Odoo
===============

Installation Options
====================

There are several ways to install Odoo, or not install it at all, depending
on your intended use case and level of expertise.

This documentation aims to provide an overview of Odoo's installation options, beginning
with two options that do not require any installation, before launching into
detailed installation instructions for each of the respective options.

.. _setup/install/demo:

Demo
----

Odoo doesn't hide itself behind a "Schedule a Demo" button and a sales pitch.
It speaks for itself and it works around you: wherever you are, whenever you are.
If you are interested in trying Odoo, but are not ready for an installation
process, this is the option for you.

To be clear, you *do not* need to install anything to start using a demo instance,
as it is accessed via your web browser.

No Registration. No Sales Pitch. Instant Access.

`Click here to start the demo <https://demo.odoo.com/>.`_

.. _setup/install/saas:

Software as a Service (SaaS)
----------------------------

So you tried the demo, fell in love with the web editor module, but are not
quite sure that you are ready to take it home. This SaaS offering
will provide you with a private instance, hosted by Odoo S.A., where
you can continue testing Odoo, using your own data. While limited to non-code
customization, it starts out free, and requires no installation.

No credit card required. Instant Access. Open Source.

`Click here to start your SaaS instance <https://www.odoo.com/page/start>.`_

Packaged Installations
----------------------

If you prefer a little more flexibility in hosting and deployment,
Odoo provides packaged installers for both Windows and Linux based operating
systems. In the case of Linux, derivatives of both Debian (e.g. Ubuntu, ...)
and Red Hat Enterprise Linux (e.g. CentOS, Fedora) are supported.

.. note:: "With great power comes great responsibility." - Uncle Ben, *Spider-Man*
          While packaged installers offer the benefit of an easy installation
          (i.e. dependencies are setup automatically), they are not managed,
          which means they may be harder to keep up-to-date. That being said,
          the packaged installers are suitable for both developing modules and
          long-term production use, given additional deployment and
          maintenance work.


`Click here to download an Official package <https://nightly.odoo.com>`_

Installation from Source Code
-----------------------------

Geared primarily towards developers, the source option is best suited for those
who are comfortable working with\u2014or around\u2014technologies used within
Odoo's development stack: programmers, database administrators, web designers,
systems administrators, et cetera. While it is the hardest option to get started
with, what the source option takes in convenience, it gives back in flexibility
For example, packaged installers don't generally give users the latitude needed
to run multiple versions of a given piece of software on a system; nor do they
provide easy access to source code. For instance, if a developer were to use
Odoo's Windows installer, they might be surprised to find the .py files are
"missing"; but that byte code (.pyc extensions) had been "left" in their place.

With that being said, the source code *can* be used as a base for both production
and long-term deployment.

.. note:: Docker users:
          An official `docker image <https://registry.hub.docker.com/_/odoo/>`_ is available.
          *See the image's help document for more information*


Installation Procedures
=======================

This section provides detailed installation instructions for each of the
installation options listed above, with the exception of the Demo and
Software as a Service (SaaS) offerings, which do not require installation.

Before You Begin
----------------

  .. danger:: Do not ignore this section

Python
******

The Odoo Project relies upon Python 2.7.9, which is an important distinction,
as there are several versions of Python 2.7 (e.g. 2.7.10, 2.7.11, ...).
We would therefore like to caution users to check for existing Python
installations before continuing with *any* of the procedures outlined below.

   .. note:: The following command is not platform specific.

**From a command prompt:**
.. code-block:: console

    > python --version
    Python 3.4.3
    > python2 --version
    Python 2.7.11

If you should see something like the above output (e.g. anything besides
Python 2.7.9), and are not sure what a "virtual environment" is,
you are in danger of overwriting one of your platform's dependencies:
please see Python's documentation concerning the use of multiple Python
installations, or follow along below.

  .. note:: Windows users:
            In this instance, "'python' is not recognized as an internal
            or external command..." is a perfectly healthy response: Python
            is not installed and so you are not in danger of overwriting
            anything.

  .. note:: Linux users:
            The situation above is easily remedied by downloading and compiling
            Python from source, using "make altinstall". See below for details.


Windows users may use `the official Python 2.7.9 installer <https://www.python.org/downloads/windows/>`_ to obtain
the appropriate Python installation, prior to installing Odoo.

    .. warning:: Windows users:
                 Select "add python.exe to Path" during installation, and
                 reboot afterwards to ensure the :envvar:`PATH` is updated.

For linux users using a distribution, such as Fedora 23, where Python 2.7.11 is the default
Python installation:

[INSTALL GUIDE]

  .. note:: [NOTE ON PREFIX and DIRs]

  .. code-block:: console

      $ ./configure --prefix
      $ make
      $ sudo make altinstall


Wkhtmltopdf
***********
[TODO: Explain usage... Warn Deb and RHEL users... Provide install guide.]

.. danger:: to print PDF reports, you must install wkhtmltopdf_ yourself:
            the version of wkhtmltopdf_ available in debian repositories does
            not support headers and footers so it can not be installed
            automatically. The recommended version is 0.12.1 and is available on
            `the wkhtmltopdf download page`_, in the archive section. As there
            is no official release for Debian Jessie, you can find ours on
            http://nightly.odoo.com/extra/.


PostgresSQL
***********

[TODO: Explain usage, as an excuse to explain what it is to Windows users;
explain Odoo's use of 9.3; Caution Fedora; Include install guide in dependency
install guide]


Node
****

[TODO: Explain what it is... Warn Deb and RHEL users... Provide install guide.
Point them back here with warning in dependency install guide.]

In Debian Wheezy, Ubuntu 13.10 and before, you will need to install
nodejs manually:

        .. code-block:: console

            $ wget -qO- https://deb.nodesource.com/setup | bash -
            $ apt-get install -y nodejs

        In later debian (>jessie) and ubuntu (>14.04) you may need to add a
        symbolic link as npm packages call ``node`` but debian calls the binary
        ``nodejs``

        .. code-block:: console

            $ apt-get install -y npm
            $ sudo ln -s /usr/bin/nodejs /usr/bin/node

GIT
****

[Potential contribs (Designers, translators, etc.), may be very skilled, but have no
VCS experience... Remove reference to zips? No contributions stuck in GIT rabbit hole.]

git allows simpler update and easier switching between different versions
of Odoo. It also simplifies maintaining non-module patches and
contributions.   Downloading it requires a `git client <http://git-scm.com/download/>`_
(which may be available via your distribution on linux) and can be performed
using the following command:



Packaged Installation on Windows
--------------------------------

* `Download Odoo's installation file<https://nightly.odoo.com/9.0/nightly/exe/odoo_9.0.latest.exe>`_
* Run the Installer.

  .. warning:: Depending on your settings, you may see a warning titled
               "Windows protected your PC". Simply click :guilabel:`More Info`
               and :guilabel:`Run anyway`.

* If asked if you want to "allow the following program to make changes...", click "Yes".
* Follow through with the rest installation process, using the Windows installer.

Odoo will automatically be started at the end of the installation.

  .. note:: Please see "Configuring Odoo", below, for configuration details.


Packaged Installation on Debian
-------------------------------

To install Odoo 9.0 on Debian-based distribution, execute the following
commands as root:

  .. code-block:: console

      # wget -O - https://nightly.odoo.com/odoo.key | apt-key add -
      # echo "deb http://nightly.odoo.com/9.0/nightly/deb/ ./" >> /etc/apt/sources.list
      # apt-get update && apt-get install odoo

This will automatically install all dependencies, install Odoo itself as a
daemon and automatically start it.


  .. note:: Please see "Configuring Odoo", below, for configuration details.

Packaged Installation on RHEL
-----------------------------

  .. warning:: with RHEL-based distributions (Red Hat Enterprise Linux, CentOS,
    Scientific Linux), EPEL_ must be added to the distribution's repositories for
    all of Odoo's dependencies to be available. For CentOS:

    .. code-block:: console

        $ sudo yum install -y epel-release

    For other RHEL-based distribution, see the EPEL_ documentation.

  .. code-block:: console

    $ sudo yum install -y postgresql-server
    $ sudo postgresql-setup initdb
    $ sudo systemctl enable postgresql
    $ sudo systemctl start postgresql
    $ sudo yum-config-manager --add-repo=https://nightly.odoo.com/9.0/nightly/rpm/odoo.repo
    $ sudo yum install -y odoo
    $ sudo systemctl enable odoo
    $ sudo systemctl start odoo

  .. danger:: to print PDF reports, you must install wkhtmltopdf_ yourself:
              the version of wkhtmltopdf_ available in Fedora/CentOS
              repositories does not support headers and footers so it can not
              be installed automatically. Use the version available on
              `the wkhtmltopdf download page`_.


.. _setup/install/source:

Source Install
==============

There are two way to get Odoo's source code: zip or git.

* Odoo zip can be downloaded from
  https://nightly.odoo.com/9.0/nightly/src/odoo_9.0.latest.zip, the zip file
  then needs to be uncompressed to use its content

  .. code-block:: console

      $ git clone https://github.com/odoo/odoo.git


Installing dependencies
-----------------------

Source installation requires manually installing dependencies:

* PostgreSQL, to use a local database

  After installation you will need to create a postgres user: by default the
  only user is ``postgres``, and Odoo forbids connecting as ``postgres``.

  - on Linux, use your distribution's package, then create a postgres user
    named like your login:

    .. code-block:: console

        $ sudo su - postgres -c "createuser -s $USER"

    Because the role login is the same as your unix login unix sockets can be
    use without a password.

  - on OS X, `postgres.app <http://postgresapp.com>`_ is the simplest way to
    get started, then create a postgres user as on Linux

  - on Windows, use `PostgreSQL for windows`_ then

    - add PostgreSQL's ``bin`` directory (default:
      ``C:\Program Files\PostgreSQL\9.4\bin``) to your :envvar:`PATH`
    - create a postgres user with a password using the pg admin gui: open
      pgAdminIII, double-click the server to create a connection, select
      :menuselection:`Edit --> New Object --> New Login Role`, enter the
      usename in the :guilabel:`Role Name` field (e.g. ``odoo``), then open
      the :guilabel:`Definition` tab and enter the password (e.g. ``odoo``),
      then click :guilabel:`OK`.

      The user and password must be passed to Odoo using either the
      :option:`-w <odoo.py -w>` and :option:`-r <odoo.py -r>` options or
      :ref:`the configuration file <reference/cmdline/config>`

* Python dependencies listed in the :file:`requirements.txt` file.

  - on Linux, python dependencies may be installable with the system's package
    manager or using pip.

    For libraries using native code (Pillow, lxml, greenlet, gevent, psycopg2,
    ldap) it may be necessary to install development tools and native
    dependencies before pip is able to install the dependencies themselves.
    These are available in ``-dev`` or ``-devel`` packages for Python,
    Postgres, libxml2, libxslt, libevent, libsasl2 and libldap2. Then the Python
    dependecies can themselves be installed:

    .. code-block:: console

        $ pip install -r requirements.txt

  - on OS X, you will need to install the Command Line Tools
    (``xcode-select --install``) then download and install a package manager
    of your choice (homebrew_, macports_) to install non-Python dependencies.
    pip can then be used to install the Python dependencies as on Linux:

    .. code-block:: console

        $ pip install -r requirements.txt

  - on Windows you need to install some of the dependencies manually, tweak the
    requirements.txt file, then run pip to install the remaining ones.

    Install ``psycopg`` using the installer here
    http://www.stickpeople.com/projects/python/win-psycopg/

    Then edit the requirements.txt file:

    - remove ``psycopg2`` as you already have it.
    - remove the optional ``python-ldap``, ``gevent`` and ``psutil`` because
      they require compilation.
    - add ``pypiwin32`` because it's needed under windows.

    Then use pip to install the dependencies using the following
    command from a cmd.exe prompt (replace ``\YourOdooPath`` by the actual
    path where you downloaded Odoo):

    .. code-block:: ps1

        C:\> cd \YourOdooPath
        C:\YourOdooPath> C:\Python27\Scripts\pip.exe install -r requirements.txt

* *Less CSS* via nodejs

  - on Linux, use your distribution's package manager to install nodejs and
    npm.

    .. warning::

        In Debian Wheezy, Ubuntu 13.10 and before, you will need to install
        nodejs manually:

        .. code-block:: console

            $ wget -qO- https://deb.nodesource.com/setup | bash -
            $ apt-get install -y nodejs

        In later debian (>jessie) and ubuntu (>14.04) you may need to add a
        symlink as npm packages call ``node`` but debian calls the binary
        ``nodejs``

        .. code-block:: console

            $ apt-get install -y npm
            $ sudo ln -s /usr/bin/nodejs /usr/bin/node

    Once npm is installed, use it to install less and less-plugin-clean-css:

    .. code-block:: console

        $ sudo npm install -g less less-plugin-clean-css

  - on OS X, install nodejs via your preferred package manager (homebrew_,
    macports_) then install less and less-plugin-clean-css:

    .. code-block:: console

        $ sudo npm install -g less less-plugin-clean-css

  - on Windows, `install nodejs <http://nodejs.org/download/>`_, reboot (to
    update the :envvar:`PATH`) and install less and less-plugin-clean-css:

    .. code-block:: ps1

        C:\> npm install -g less less-plugin-clean-css


Configuring Odoo
================

    [Introduction/Clarification]

Configuring Odoo for Windows
''''''''''''''''''''''''''''

The :ref:`configuration file <reference/cmdline/config>` can be found at
:file:`{%PROGRAMFILES%}\\Odoo 9.0-{id}\\server\\openerp-server.conf`.

The configuration file can be edited to connect to a remote Postgresql, edit
file locations or set a dbfilter.

To reload the configuration file, restart the Odoo service via
:menuselection:`Services --> odoo server`.

Configuring Odoo for Debian
'''''''''''''''''''''''''''

The :ref:`configuration file <reference/cmdline/config>` can be found at
:file:`/etc/odoo/openerp-server.conf`

When the configuration file is edited, Odoo must be restarted using
``service``:

.. code-block:: console

    $ sudo service odoo restart
    Restarting odoo: ok

Configuring Odoo for RHEL
'''''''''''''''''''''''''

The :ref:`configuration file <reference/cmdline/config>` can be found at
:file:`/etc/odoo/openerp-server.conf`

When the configuration file is edited, Odoo must be restarted via SystemD:

.. code-block:: console

    $ sudo systemctl restart odoo


Configuring Odoo for Source
'''''''''''''''''''''''''''


Running Odoo
============

Running Odoo on Windows
-----------------------
[Note If you've installed via Packaged...]
Once all dependencies are set up, Odoo can be launched by running ``odoo.py``.

:ref:`Configuration <reference/cmdline>` can be provided either through
:ref:`command-line arguments <reference/cmdline>` or through a
:ref:`configuration file <reference/cmdline/config>`.


Under Windows a typical way to execute odoo would be:

.. code-block:: ps1

    C:\YourOdooPath> python odoo.py -w odoo -r odoo --addons-path=addons,../mymodules --db-filter=mydb$

Where ``odoo``, ``odoo`` are the postgresql login and password,
``../mymodules`` a directory with additional addons and ``mydb`` the default
db to serve on localhost:8069

Running Odoo on Linux
---------------------
Under Unix a typical way to execute odoo would be:

.. code-block:: console

    $ ./odoo.py --addons-path=addons,../mymodules --db-filter=mydb$

Where ``../mymodules`` is a directory with additional addons and ``mydb`` the
default db to serve on localhost:8069



.. _demo: https://demo.odoo.com
.. _docker: https://www.docker.com
.. _EPEL: https://fedoraproject.org/wiki/EPEL
.. _PostgreSQL: http://www.postgresql.org
.. _the official installer:
.. _install pip:
    https://pip.pypa.io/en/latest/installing.html#install-pip
.. _PostgreSQL for windows:
    http://www.enterprisedb.com/products-services-training/pgdownload
.. _Quilt: http://en.wikipedia.org/wiki/Quilt_(software)
.. _saas: https://www.odoo.com/page/start
.. _the wkhtmltopdf download page: http://wkhtmltopdf.org/downloads.html
.. _wkhtmltopdf: http://wkhtmltopdf.org
.. _pip: https://pip.pypa.io
.. _macports: https://www.macports.org
.. _homebrew: http://brew.sh
.. _Visual C++ Compiler for Python 2.7:
    http://www.microsoft.com/en-us/download/details.aspx?id=44266
.. _wheels: https://wheel.readthedocs.org/en/latest/
.. _virtual environment: http://docs.python-guide.org/en/latest/dev/virtualenvs/
.. _pywin32: http://sourceforge.net/projects/pywin32/files/pywin32/
.. _the repository: https://github.com/odoo/odoo
.. _git: http://git-scm.com
