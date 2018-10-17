:banner: banners/installing_odoo.jpg

.. _setup/install:

===============
Installing Odoo
===============

There are multiple ways to install Odoo, or not install it at all, depending
on the intended use case.

This documents attempts to describe most of the installation options.

:ref:`setup/install/online`
    The easiest way to use Odoo in production or to try it.

:ref:`setup/install/packaged`
    Suitable for testing Odoo, developing modules and can be used for
    long-term production use with additional deployment and maintenance work.

:ref:`setup/install/source`
    Provides greater flexibility:  e.g. allow multiple running Odoo versions on
    the same system. Good for developing modules, can be used as base for
    production deployment.

:ref:`setup/install/docker`
    If you usually use docker_ for development or deployment, an official
    docker_ base image is available.

.. _setup/install/editions:

Editions
========

There are two different Editions_ of Odoo: the Community and Enterprise versions.
Using the Enterprise version is possible on our SaaS_ and accessing the code is
restricted to Enterprise customers and partners. The Community version is freely
available to anyone.

If you already use the Community version and wish to upgrade to Enterprise, please
refer to :ref:`setup/enterprise` (except for :ref:`setup/install/source`).

.. _setup/install/online:

Online
======

Demo
----

To simply get a quick idea of Odoo, demo_ instances are available. They are
shared instances which only live for a few hours, and can be used to browse
around and try things out with no commitment.

Demo_ instances require no local installation, just a web browser.

SaaS
----

Trivial to start with, fully managed and migrated by Odoo S.A., Odoo's SaaS_
provides private instances and starts out free. It can be used to discover and
test Odoo and do non-code customizations (i.e. incompatible with custom modules
or the Odoo Apps Store) without having to install it locally.

Can be used for both testing Odoo and long-term production use.

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

Linux
-----

Debian/Ubuntu
'''''''''''''

Odoo 12.0 'deb' package currently supports `Debian Stretch`_, `Ubuntu 18.04`_ or above.

Prepare
^^^^^^^

Odoo needs a `PostgreSQL`_ server to run properly. The default configuration for
the Odoo 'deb' package is to use the PostgreSQL server on the same host as your
Odoo instance. Execute the following command as root in order to install
PostgreSQL server :

.. code-block:: console

  # apt-get install postgresql -y

In order to print PDF reports, you must install wkhtmltopdf_ yourself:
the version of wkhtmltopdf_ available in debian repositories does not support
headers and footers so it can not be installed automatically.
The recommended version is 0.12.1 and is available on `the wkhtmltopdf download page`_,
in the archive section.

Repository
^^^^^^^^^^

Odoo S.A. provides a repository that can be used with  Debian and Ubuntu
distributions. It can be used to install Odoo Community Edition by executing the
following commands as root:

.. code-block:: console

    # wget -O - https://nightly.odoo.com/odoo.key | apt-key add -
    # echo "deb http://nightly.odoo.com/12.0/nightly/deb/ ./" >> /etc/apt/sources.list.d/odoo.list
    # apt-get update && apt-get install odoo

You can then use the usual ``apt-get upgrade`` command to keep your installation up-to-date.

At this moment, there is no repository for the Enterprise Edition.

Deb Package
^^^^^^^^^^^

Instead of using the repository as described above, the 'deb' package can be
downloaded here:

* Community Edition: `nightly`_
* Enterprise Edition `Download`_

You can then use ``gdebi``:

.. code-block:: console

    # gdebi <path_to_installation_package>

Or ``dpkg``:

.. code-block:: console

    # dpkg -i <path_to_installation_package> # this probably fails with missing dependencies
    # apt-get install -f # should install the missing dependencies
    # dpkg -i <path_to_installation_package>

This will install Odoo as a service, create the necessary PostgreSQL_ user
and automatically start the server.

.. warning:: The 3 following python packages are only suggested by the Debian package.
             Those packages are not available in Ubuntu Xenial (16.04).

* python3-vobject: Used in calendars to produce ical files.
* python3-pyldap: Used to authenticat users with LDAP.
* python3-qrcode: Used by the hardware driver for ESC/POS

If you need one or all of the packages mentioned in the above warning, you can install them manually.
One way to do it, is simply using pip3 like this:

.. code-block:: console

    $ sudo pip3 install vobject qrcode
    $ sudo apt install libldap2-dev libsasl2-dev
    $ sudo pip3 install pyldap

.. warning:: Debian 9 and Ubuntu do not provide a package for the python module
             num2words.
             Textual amounts will not be rendered by Odoo and this could cause
             problems with the "l10n_mx_edi" module.

If you need this feature, you can install the python module like this:

.. code-block:: console

    $ sudo pip3 install num2words

Fedora
''''''

Odoo 12.0 'rpm' package supports Fedora 26.
As of 2017, CentOS does not have the minimum Python requirements (3.5) for
Odoo 12.0.

Prepare
^^^^^^^
Odoo needs a `PostgreSQL`_ server to run properly. Assuming that the 'sudo'
command is available and configured properly, run the following commands :

.. code-block:: console

    $ sudo dnf install -y postgresql-server
    $ sudo postgresql-setup --initdb --unit postgresql
    $ sudo systemctl enable postgresql
    $ sudo systemctl start postgresql

In order to print PDF reports, you must install wkhtmltopdf_ yourself:
the version of wkhtmltopdf_ available in debian repositories does not support
headers and footers so it can not be installed automatically.
The recommended version is 0.12.1 and is available on `the wkhtmltopdf download page`_,
in the archive section.

Repository
^^^^^^^^^^

Odoo S.A. provides a repository that can be used with the Fedora distibutions.
It can be used to install Odoo Community Edition by executing the following
commands:

.. code-block:: console

    $ sudo dnf config-manager --add-repo=https://nightly.odoo.com/12.0/nightly/rpm/odoo.repo
    $ sudo dnf install -y odoo
    $ sudo systemctl enable odoo
    $ sudo systemctl start odoo

RPM package
^^^^^^^^^^^

Instead of using the repository as described above, the 'rpm' package can be
downloaded here:

* Community Edition: `nightly`_
* Enterprise Edition `Download`_

Once downloaded, the package can be installed using the 'dnf' package manager:

.. code-block:: console

    $ sudo dnf localinstall odoo_12.0.latest.noarch.rpm
    $ sudo systemctl enable odoo
    $ sudo systemctl start odoo

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

Prepare
-------

Source installation requires manually installing dependencies:

* Python 3.5+.

  - on Linux and OS X, using your package manager if not installed by default

    .. note:: on some system, ``python`` command refers to Python 2 (outdated)
              or to Python 3 (supported). Make sure you are using the right
              version and that the alias ``python3`` is present in your
              :envvar:`PATH`

  - on Windows, use `the official Python 3 installer
    <https://www.python.org/downloads/windows/>`_.

    .. warning:: select "add python.exe to Path" during installation, and
                 reboot afterwards to ensure the :envvar:`PATH` is updated

    .. note:: if Python is already installed, make sure it is 3.5 or above,
              previous versions are not compatible with Odoo.

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

        $ pip3 install -r requirements.txt

  - on OS X, you will need to install the Command Line Tools
    (``xcode-select --install``) then download and install a package manager
    of your choice (homebrew_, macports_) to install non-Python dependencies.
    pip can then be used to install the Python dependencies as on Linux:

    .. code-block:: console

        $ pip3 install -r requirements.txt

  - on Windows you need to install some of the dependencies manually, tweak the
    requirements.txt file, then run pip to install the remaning ones.

    Install ``psycopg`` using the installer here
    http://www.stickpeople.com/projects/python/win-psycopg/

    Then use pip to install the dependencies using the following
    command from a cmd.exe prompt (replace ``\YourOdooPath`` by the actual
    path where you downloaded Odoo):

    .. code-block:: doscon

        C:\> cd \YourOdooPath
        C:\YourOdooPath> C:\Python35\Scripts\pip.exe install -r requirements.txt

* *RTLCSS* via nodejs

  For languages with right-to-left interface (such as Arabic or Hebrew), the
  package ``rtlcss`` is needed.

  - on Linux, use your distribution's package manager to install nodejs and
    npm.
    Once npm is installed, use it to install rtlcss:

    .. code-block:: console

        $ sudo npm install -g rtlcss

  - on OS X, install nodejs via your preferred package manager (homebrew_,
    macports_) then install less:

    .. code-block:: console

        $ sudo npm install -g rtlcss

  - on Windows, `install nodejs <https://nodejs.org/en/download/>`_, reboot (to
    update the :envvar:`PATH`) and install rtlcss:

    .. code-block:: doscon

        C:\> npm install -g rtlcss

    It is then necessary to edit the System Environment's variable
    :envvar:`PATH` and add the folder where `rtlcss.cmd` is located. Typically:

    .. code-block:: console

        C:\Users\<user>\AppData\Roaming\npm\


Fetch the sources
-----------------

There are two ways to obtain the Odoo source code: zip or git.

* Odoo zip can be downloaded from  our nightly_ server or our Download_  page,
  the zip file then needs to be uncompressed to use its content

* git allows simpler update and easier switching between different versions
  of Odoo. It also simplifies maintaining non-module patches and
  contributions.  The primary drawback of git is that it is significantly
  larger than a tarball as it contains the entire history of the Odoo project.

Community Edition
'''''''''''''''''

The git repository is https://github.com/odoo/odoo.git for the Community
edition.

Downloading it requires a `git client <http://git-scm.com/download/>`_
(which may be available via your distribution on linux) and can be performed
using the following command:

.. code-block:: console

    $ git clone https://github.com/odoo/odoo.git

Enterprise Edition
''''''''''''''''''

If you have access to the Enterprise repository (see :ref:`setup/install/editions`
if you wish to get access), you can use this command to fetch the addons:

.. code-block:: console

  $ git clone https://github.com/odoo/enterprise.git

.. note:: The Enterprise git repository **does not contain the full Odoo
    source code**. It is only a collection of extra add-ons. The main server
    code is in the Community version.  Running the Enterprise version actually
    means running the server from the Community version with the addons-path option
    set to the folder with the Enterprise version.

    You need to clone both the Community and Enterprise repository to have a working
    Odoo installation

Running Odoo
------------

Once all dependencies are set up, Odoo can be launched by running ``odoo-bin``.

.. tip:: For the Enterprise edition, you must specify the :file:`enterprise`
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

.. code-block:: doscon

    C:\YourOdooPath> python3 odoo-bin -w odoo -r odoo --addons-path=addons,../mymodules --db-filter=mydb$

Where ``odoo``, ``odoo`` are the postgresql login and password,
``../mymodules`` a directory with additional addons and ``mydb`` the default
db to serve on localhost:8069

Under Unix a typical way to execute odoo would be:

.. code-block:: console

    $ ./odoo-bin --addons-path=addons,../mymodules --db-filter=mydb$

Where ``../mymodules`` is a directory with additional addons and ``mydb`` the
default db to serve on localhost:8069

Virtualenv
----------

Virtualenv_ is a tool to create Python isolated environments because it's
sometimes preferable to not mix your distribution python modules packages
with globally installed python modules with pip.

This section will explain how to run Odoo in a such isolated Python environment.

Here we are going to use virtualenvwrapper_ which is a set of shell scripts that
makes the use of virtualenv easier.

The examples below are based on a Debian 9 distribution but could be adapted on
any platform where virtualenvwrapper_ and virtualenv_ are able to run.

This section assumes that you obtained the Odoo sources from the zip file or the
git repository as explained above. The same apply for postgresql installation
and configuration.

Install virtualenvwrapper
'''''''''''''''''''''''''

.. code-block:: console

  $ sudo apt install virtualenvwrapper
  $ source /usr/share/virtualenvwrapper/virtualenvwrapper.sh

This will install virtualenvwrapper_ and activate it immediately.
Now, let's install the tools required to build Odoo dependencies if needed:

.. code-block:: console

  $ sudo apt install build-essential python3-dev libxslt-dev libzip-dev libldap2-dev libsasl2-dev

Create an isolated environment
''''''''''''''''''''''''''''''

Now we can create a virtual environment for Odoo like this:

.. code-block:: console

  $ mkvirtualenv -p /usr/bin/python3 odoo-venv

With this command, we ask for an isolated Python3 environment that will be named
"odoo-env". If the command works as expected, your shell is now using this
environment. Your prompt should have changed to remind you that you are using
an isolated environment. You can verify with this command:

.. code-block:: console

  $ which python3

This command should show you the path to the Python interpreter located in the
isolated environment directory.

Now let's install the Odoo required python packages:

.. code-block:: console

  $ cd your_odoo_sources_path
  $ pip install -r requirements.txt

After a little while, you should be ready to run odoo from the command line as
explained above.

When you you want to leave the virtual environment, just issue this command:

.. code-block:: console

  $ deactivate

Whenever you want to work again with your 'odoo-venv' environment:

.. code-block:: console

  $ workon odoo-venv

.. _setup/install/docker:

Docker
======

The full documentation on how to use Odoo with Docker can be found on the
official Odoo `docker image <https://registry.hub.docker.com/_/odoo/>`_ page.

.. _demo: https://demo.odoo.com
.. _docker: https://www.docker.com
.. _Download: https://www.odoo.com/page/download
.. _Debian Stretch: https://www.debian.org/releases/stretch/
.. _Ubuntu 18.04: http://releases.ubuntu.com/18.04/
.. _EPEL: https://fedoraproject.org/wiki/EPEL
.. _PostgreSQL: http://www.postgresql.org
.. _the official installer:
.. _install pip:
    https://pip.pypa.io/en/latest/installing.html#install-pip
.. _PostgreSQL for windows:
    http://www.enterprisedb.com/products-services-training/pgdownload
.. _Quilt: http://en.wikipedia.org/wiki/Quilt_(software)
.. _saas: https://www.odoo.com/page/start
.. _the wkhtmltopdf download page: https://github.com/wkhtmltopdf/wkhtmltopdf/releases/tag/0.12.1
.. _UAC: http://en.wikipedia.org/wiki/User_Account_Control
.. _wkhtmltopdf: http://wkhtmltopdf.org
.. _pip: https://pip.pypa.io
.. _macports: https://www.macports.org
.. _homebrew: http://brew.sh
.. _wheels: https://wheel.readthedocs.org/en/latest/
.. _virtualenv: https://pypi.python.org/pypi/virtualenv
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/en/latest/
.. _pywin32: http://sourceforge.net/projects/pywin32/files/pywin32/
.. _the repository: https://github.com/odoo/odoo
.. _git: http://git-scm.com
.. _Editions: https://www.odoo.com/pricing#pricing_table_features
.. _nightly: https://nightly.odoo.com/12.0/nightly/
.. _extra: https://nightly.odoo.com/extra/
