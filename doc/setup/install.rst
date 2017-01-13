:banner: banners/installing_odoo.jpg

.. _setup/install:

===============
Installing Odoo
===============

There are mutliple ways to install Odoo, or not install it at all, depending
on the intended use case.

This documents attempts to describe most of the installation options.

:ref:`setup/install/demo`
    The simplest "installation", only suitable for getting a quick feel for
    Odoo or trying something out
:ref:`setup/install/saas`
    Trivial to start with and fully managed and migrated by Odoo S.A., can be
    used to both test Odoo and use it for your business, prevents complex
    customization (i.e. incompatible with custom modules or the Odoo Apps Store).

    Can be used for both testing Odoo and long-term production use.
:ref:`setup/install/packaged`
    Simple to get started, allows more flexibility in hosting and deploying
    the system and greater control over where data is stored. The maintenance
    burden is shifted to the user.

    Suitable for testing Odoo, developing modules and can be used for
    long-term production use with additional deployment and maintenance work.
:ref:`setup/install/source`
    Harder to get started than :ref:`setup/install/packaged`, provides
    even greater flexibility: packaged installers don't generally allow
    multiple running Odoo versions on the same system, and don't provide easy
    source access to Odoo itself.

    Good for developing modules, can be used as base for production
    deployment.

    The source code can be obtained by downloading a tarball or using git.
    Using git is strongly advised, as it makes it easier to update, switch
    between multiple versions (including the current development version)
    or contribute.
`docker image <https://registry.hub.docker.com/_/odoo/>`_
    If you usually use docker_ for development or deployment, an official
    docker_ base image is available, see the image's help document for more
    information.

.. _setup/install/editions:

Editions
========

There are two different Editions_ of Odoo: the Community and Enterprise versions.
Using the Enterprise version is possible on our SaaS_ and accessing the code is
restricted to Enterprise customers and partners. The Community version is freely
available to anyone.

If you already use the Community version and wish to upgrade to Enterprise, please
refer to :ref:`setup/enterprise` (except for :ref:`setup/install/source`).

If you wish to access the Enterprise installers/source code, you can:

* Go to the Download_ page and log in with your customer credentials
* Download the source on GitHub using git_(available to partners only)

.. note:: If you do not have access to our Enterprise repository, you can request
    it be e-mailing your sales representative or our online support with
    your subscription number and GitHub username. (available to partners only)

.. warning:: Enterprise deb and rpm packages do not have repositories, so automatic
    update will not work. Reinstalling the latest package version will be needed
    to update manually an installation.

.. _setup/install/demo:

Demo
====

To simply get a quick idea of Odoo, demo_ instances are available. They are
shared instances which only live for a few hours, and can be used to browse
around and try things out with no commitment.

Demo_ instances require no local installation, just a web browser.

.. _setup/install/saas:

SaaS
====

Odoo's SaaS_ provides private instances and starts out free. It can be used to
discover and test Odoo and do non-code customizations without having to
install it locally.

Like demo_ instances, SaaS_ instances require no local installation, a web
browser is sufficient.

.. _setup/install/packaged:

Packaged installers
===================

Odoo provides packaged installers for Windows, deb-based distributions
(Debian, Ubuntu, …) and RPM-based distributions (Fedora, CentOS, RHEL, …) for
both the Community and Enterprise versions.

These packages automatically set up all dependencies (for the Community version),
but may be difficult to keep up-to-date.

Official Community packages with all relevant dependency requirements are
available on our nightly_ server. Both Communtiy and Enterprise packages can
be downloaded from our Download_ page (you must to be logged in as a paying
customer or partner to download the Enterprise packages).

Windows
-------

* Download the installer from our nightly_ server (Community only)
  or the Windows installer from the Download_ page (any edition)
* Run the downloaded file

  .. warning:: on Windows 8, you may see a warning titled "Windows protected
               your PC". Click :guilabel:`More Info` then
               :guilabel:`Run anyway`

* Accept the UAC_ prompt
* Go through the various installation steps

Odoo will automatically be started at the end of the installation.

Configuration
'''''''''''''

The :ref:`configuration file <reference/cmdline/config>` can be found at
:file:`{%PROGRAMFILES%}\\Odoo 10.0-{id}\\server\\odoo.conf`.

The configuration file can be edited to connect to a remote Postgresql, edit
file locations or set a dbfilter.

To reload the configuration file, restart the Odoo service via
:menuselection:`Services --> odoo server`.

Deb
---

Community
'''''''''

To install Odoo 10.0 Community on Debian-based distribution, execute the following
commands as root:

.. code-block:: console

    # wget -O - https://nightly.odoo.com/odoo.key | apt-key add -
    # echo "deb http://nightly.odoo.com/10.0/nightly/deb/ ./" >> /etc/apt/sources.list.d/odoo.list
    # apt-get update && apt-get install odoo

You can then use the usual ``apt-get upgrade`` command to keep your installation up-to-date.

Enterprise
''''''''''

For Odoo 10.0 Enterprise, get the package from the Download_ page. You can then
use ``gdebi``:

.. code-block:: console

    # apt-get install postgresql -y
    # gdebi <path_to_installation_package>

Or ``dpkg`` (handles less dependencies automatically):

.. code-block:: console

    # apt-get install postgresql -y
    # dpkg -i <path_to_installation_package> # this probably fails with missing dependencies
    # apt-get install -f # should install the missing dependencies
    # dpkg -i <path_to_installation_package>


This will install Odoo as a service, create the necessary PostgreSQL_ user
and automatically start the server.

.. danger:: to print PDF reports, you must install wkhtmltopdf_ yourself:
            the version of wkhtmltopdf_ available in debian repositories does
            not support headers and footers so it can not be installed
            automatically. The recommended version is 0.12.1 and is available on
            `the wkhtmltopdf download page`_, in the archive section. As there
            is no official release for Debian Jessie, you can find ours on the
            extra_ section of our nightly server.

Configuration
'''''''''''''

The :ref:`configuration file <reference/cmdline/config>` can be found at
:file:`/etc/odoo/odoo.conf`

When the configuration file is edited, Odoo must be restarted using
``service``:

.. code-block:: console

    $ sudo service odoo restart
    Restarting odoo: ok

RPM
---

.. warning::

    with RHEL-based distributions (RHEL, CenOS, Scientific Linux), EPEL_ must
    be added to the distribution's repositories for all of Odoo's
    dependencies to be available. For CenOS:

    .. code-block:: console

        $ sudo yum install -y epel-release

    For other RHEL-based distribution, see the EPEL_ documentation.

Community
'''''''''

Execute the following commands to install Odoo 10.0 Community on your server:

.. code-block:: console

    $ sudo yum install -y postgresql-server
    $ sudo postgresql-setup initdb
    $ sudo systemctl enable postgresql
    $ sudo systemctl start postgresql
    $ sudo yum-config-manager --add-repo=https://nightly.odoo.com/10.0/nightly/rpm/odoo.repo
    $ sudo yum install -y odoo
    $ sudo systemctl enable odoo
    $ sudo systemctl start odoo

Enterprise
''''''''''

For Odoo 10.0 Enterprise, get the package from the Download_ page. Then run:

.. code-block:: console

    $ sudo yum install -y postgresql-server
    $ sudo postgresql-setup initdb
    $ sudo systemctl enable postgresql
    $ sudo systemctl start postgresql
    $ sudo yum localinstall odoo_10.0.latest.noarch.rpm
    $ sudo systemctl enable odoo
    $ sudo systemctl start odoo


.. danger:: to print PDF reports, you must install wkhtmltopdf_ yourself:
            the version of wkhtmltopdf_ available in Fedora/CentOS
            repositories does not support headers and footers so it can not
            be installed automatically. Use the version available on
            `the wkhtmltopdf download page`_.

Configuration
'''''''''''''

The :ref:`configuration file <reference/cmdline/config>` can be found at
:file:`/etc/odoo/odoo.conf`

When the configuration file is edited, Odoo must be restarted via SystemD:

.. code-block:: console

    $ sudo systemctl restart odoo


.. _setup/install/source:

Source Install
==============

The source "installation" really is about not installing Odoo, and running
it directly from source instead.

This can be more convenient for module developers as the Odoo source is
more easily accessible than using packaged installation (for information or
to build this documentation and have it available offline).

It also makes starting and stopping Odoo more flexible and explicit than the
services set up by the packaged installations, and allows overriding settings
using :ref:`command-line parameters <reference/cmdline>` without needing to
edit a configuration file.

Finally it provides greater control over the system's set up, and allows more
easily keeping (and running) multiple versions of Odoo side-by-side.

Community
---------

There are two way to get the odoo source source zip or git.

* Odoo zip can be downloaded from  our nightly_ server or our Download_  page,
  the zip file then needs to be uncompressed to use its content

* git allows simpler update and easier switching between different versions
  of Odoo. It also simplifies maintaining non-module patches and
  contributions.  The primary drawback of git is that it is significantly
  larger than a tarball as it contains the entire history of the Odoo project.

  The git repository is https://github.com/odoo/odoo.git for the Community
  version.

  Downloading it requires a `git client <http://git-scm.com/download/>`_
  (which may be available via your distribution on linux) and can be performed
  using the following command:

  .. code-block:: console

      $ git clone https://github.com/odoo/odoo.git

Enterprise
----------

If you have access to the Enterprise repository (see :ref:`setup/install/editions`
if you wish to get access), you can use this command to fetch the addons:

.. code-block:: console

  $ git clone https://github.com/odoo/enterprise.git

If you use git_, you must modify the :option:`--addons-path <odoo-bin --addons-path>`
parameter of your launch command (``init.d``, custom script, configuration file,
etc.). The Enterprise addons folder should be included **before** the default
addons folder.

For example:

.. code-block:: console

  $ odoo-bin --addons-path=~/src/custom_modules,~/src/enterprise,~/src/odoo/addons

.. warning:: The Enterprise git repository **does not contain the full Odoo
    source code**. You need to clone both the Community and Enterprise repository to
    have a working Odoo installation. The Download_ page contains the entire
    source code but is not updateable as easily.


Installing dependencies
-----------------------

Source installation requires manually installing dependencies:

* Python 2.7.

  - on Linux and OS X, included by default
  - on Windows, use `the official Python 2.7.9 installer
    <https://www.python.org/downloads/windows/>`_.

    .. warning:: select "add python.exe to Path" during installation, and
                 reboot afterwards to ensure the :envvar:`PATH` is updated

    .. note:: if Python is already installed, make sure it is 2.7.9, previous
              versions are less convenient and 3.x versions are not compatible
              with Odoo

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
      :option:`-w <odoo-bin -w>` and :option:`-r <odoo-bin -r>` options or
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
    requirements.txt file, then run pip to install the remaning ones.

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

        In debian wheezy and Ubuntu 13.10 and before you need to install
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

    Once npm is installed, use it to install less:

    .. code-block:: console

        $ sudo npm install -g less

  - on OS X, install nodejs via your preferred package manager (homebrew_,
    macports_) then install less:

    .. code-block:: console

        $ sudo npm install -g less

  - on Windows, `install nodejs <http://nodejs.org/download/>`_, reboot (to
    update the :envvar:`PATH`) and install less:

    .. code-block:: ps1

        C:\> npm install -g less

Running Odoo
------------

Once all dependencies are set up, Odoo can be launched by running ``odoo-bin``.

.. warning:: For the Enterprise edition, you must specify the :file:`enterprise`
    addons folder when starting your server. You can do so by providing the path
    to your :file:`enterprise` folder in the ``addons-path`` parameter. Please
    note that the :file:`enterprise` folder must come before the default
    :file:`addons` folder in the  list for the addons to be loaded correctly.

:ref:`Configuration <reference/cmdline>` can be provided either through
:ref:`command-line arguments <reference/cmdline>` or through a
:ref:`configuration file <reference/cmdline/config>`.

Common necessary configurations are:

* PostgreSQL host, port, user and password.

  Odoo has no defaults beyond
  `psycopg2's defaults <http://initd.org/psycopg/docs/module.html>`_: connects
  over a UNIX socket on port 5432 with the current user and no password. By
  default this should work on Linux and OS X, but it *will not work* on
  windows as it does not support UNIX sockets.

* Custom addons path beyond the defaults, to load your own modules

Under Windows a typical way to execute odoo would be:

.. code-block:: ps1

    C:\YourOdooPath> python odoo-bin -w odoo -r odoo --addons-path=addons,../mymodules --db-filter=mydb$

Where ``odoo``, ``odoo`` are the postgresql login and password,
``../mymodules`` a directory with additional addons and ``mydb`` the default
db to serve on localhost:8069

Under Unix a typical way to execute odoo would be:

.. code-block:: console

    $ ./odoo-bin --addons-path=addons,../mymodules --db-filter=mydb$

Where ``../mymodules`` is a directory with additional addons and ``mydb`` the
default db to serve on localhost:8069

.. _demo: https://demo.odoo.com
.. _docker: https://www.docker.com
.. _Download: https://www.odoo.com/page/download
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
.. _UAC: http://en.wikipedia.org/wiki/User_Account_Control
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
.. _Editions: https://www.odoo.com/pricing#pricing_table_features
.. _nightly: https://nightly.odoo.com/10.0/nightly/
.. _extra: https://nightly.odoo.com/extra/
