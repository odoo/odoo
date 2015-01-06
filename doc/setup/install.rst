.. _setup/install:

===============
Installing Odoo
===============

There are mutliple ways to install Odoo, or not install it at all, depending
on the intended use case.

This documents attempts to describe most of the installation options.

:ref:`setup/install/demo`
    the simplest "installation", only suitable for getting a quick feel for
    Odoo or trying something out
:ref:`setup/install/saas`
    trivial to start with and fully managed and migrated by Odoo S.A., can be
    used to both test Odoo and use it for your business, but restricts the
    flexibility of the system somewhat (check: no custom modules? what else?).

    Can be used for both testing Odoo and long-term "production" use.
:ref:`setup/install/packaged`
    simple to get started, allows more flexibility in hosting and deploying
    the system and greater control over where data is stored. The maintenance
    burden is shifted to the user.

    Suitable for testing Odoo, developing modules and can be used for
    long-term production use with additional deployment and maintenance work.
:ref:`setup/install/source`
    harder to get started than :ref:`setup/install/packaged`, provides
    even greater flexibility: packaged installers don't generally allow
    multiple running Odoo versions on the same system, and don't provide easy
    source access to Odoo itself.

    Good for developing modules, can be used as base for production
    deployment.
:ref:`setup/install/vcs`
    Mostly has the same strengths and weaknesses as the
    :ref:`setup/install/source`, but allows (technically) simpler
    switching between versions of Odoo, as well as more structured patching
    and customisations of Odoo itself (not through custom modules): with a
    standard :ref:`setup/install/source`, a custom solution has to be
    implemented to keep track of patches applied to Odoo (e.g. Quilt_). With
    a VCS checkout, these changes can be implemented as standard Git revisions
    or a custom Git branch, and can more easily be contributed back to the
    main project.

.. _setup/install/demo:

Demo_
=====

To simply get a quick idea of Odoo, demo_ instances are available. They are
shared instances which only live for a few hours, and can be used to browse
around and try things out with no commitment.

Demo_ instances require no local installation, just a web browser.

.. _setup/install/saas:

SaaS_
=====

Odoo's SaaS_ provides private instances and starts out free. It can be used to
discover and test Odoo and do non-code customizations without having to
install it locally.

Like demo_ instances, SaaS_ instances require no local installation, a web
browser is sufficient.

.. _setup/install/packaged:

Packaged installers
===================

.. Odoo provides packaged installers for Windows, deb-based distributions
.. (Debian, Ubuntu, …) and RPM-based distributions (Fedora, CentOS, RHEL, …).

Odoo provides packaged installers for Windows and deb-based distributions
(Debian, Ubuntu, …).

These packages automatically set up all dependencies, but may be difficult to
keep up-to-date.

Official packages with all relevant dependency requirements are available on
https://nightly.odoo.com.

Deb
---

To install Odoo 8.0 on Debian-based distribution, execute the following
commands as root:

.. code-block:: console

    # wget -O - https://nightly.odoo.com/odoo.key | apt-key add -
    # echo "deb http://nightly.odoo.com/8.0/nightly/deb/ ./" >> /etc/apt/sources.list
    # apt-get update && apt-get install odoo

This will automatically install all dependencies, install Odoo itself as a
daemon and automatically start it.

.. postgres-server apparently automatically installed due to being a
   recommended package, maybe install it explicitly for the purpose of this
   document?

.. danger:: to print PDF reports, you must install wkhtmltopdf_ yourself:
            the version of wkhtmltopdf_ available in debian repositories does
            not support headers and footers so it can not be installed
            automatically. Use the version available on
            `the wkhtmltopdf download page`_.

Configuration
'''''''''''''

The :ref:`configuration file <reference/cmdline/config>` can be found at
:file:`/etc/odoo/openerp-server.conf`

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

.. code-block:: console

    $ sudo yum install -y postgresql-server
    $ sudo postgresql-setup initdb
    $ sudo systemctl enable postgresql
    $ sudo systemctl start postgresql
    $ sudo yum-config-manager --add-repo=https://nightly.odoo.com/8.0/nightly/rpm/odoo.repo
    $ sudo yum install -y odoo
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
:file:`/etc/odoo/openerp-server.conf`

When the configuration file is edited, Odoo must be restarted via SystemD:

.. code-block:: console

    $ sudo systemctl restart odoo

Windows
-------

* download https://nightly.odoo.com/8.0/nightly/exe/odoo_8.0.latest.exe
* run the downloaded file

  .. warning:: on Windows 8, you may see a warning titled "Windows protected
               your PC". Click :guilabel:`More Info` then
               :guilabel:`Run anyway`

* Accept the UAC_ prompt
* Go through the various installation steps

Odoo will automatically be started at the end of the installation.

Configuration
'''''''''''''

The :ref:`configuration file <reference/cmdline/config>` can be found at
:file:`{%PROGRAMFILES%}\\Odoo 8.0-{id}\\server\\openerp-server.conf`.

The configuration file can be edited to connect to a remote Postgresql, edit
file locations or set a dbfilter.

To reload the configuration file, restart the Odoo service via
:menuselection:`Services --> odoo server`.

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

The Odoo source can be downloaded from
https://nightly.odoo.com/8.0/nightly/src/odoo_8.0-latest.tar.gz

.. warning:: Windows does not handle .tar.gz archives natively, you will have
             to download and install `7-Zip <http://www.7-zip.org>`_ to
             decompress the archive

Installing dependencies
-----------------------

Source installation requires manually installing dependencies, be them native
dependencies or Python libraries:

* Python, should be preinstalled on most systems. On Windows, use `the
  official Python 2.7 installer <https://www.python.org/downloads/windows/>`_.

* PostgreSQL, if you want the database to be on the same machine as Odoo
  (simplest and default)

  - on Linux, use your distribution's package
  - on Windows, use `the official installer`_
  - on OS X, `postgres.app <http://postgresapp.com>`_ is the simplest way to
    get started

  .. todo:: create new role?

* the :file:`requirements.txt` file in the source lists all the Python
  dependencies

  - for Windows, http://www.lfd.uci.edu/~gohlke/pythonlibs/ provides a number
    of libraries, for both pure-python and native, packaged as installers
  - dependencies may be installable with the system's package manager
  - pip_ can take the requirements file directly and install everything listed
    in it, either globally or within a `virtual environment`_:

    .. code-block:: console

        $ pip install -r path/to/requirements.txt

    For libraries using native code (Pillow, lxml, greenlet, gevent, psycopg2)
    it may be necessary to install development tools and native dependencies
    before pip is able to install the dependencies themselves:

    * Linux distributions generally require ``-dev`` or ``-devel`` packages
      for Python, Postgres, libxml2, libxslt and libevent
    * for OSX, install the Command Line Tools (``xcode-select --install``) the
      native dependency via your preferred package manager (macports_,
      homebrew_)
    * for Windows

      .. danger:: you will have to remove ``python-ldap`` from the
                  requirements file, it can not be installed via pip_ on
                  Windows and must be installed as a precompiled binary

      - install the `Visual C++ Compiler for Python 2.7`_ (and restart)
      - install `PostgreSQL for windows`_ if not already done
      - Add PostgreSQL's ``bin`` directory (default:
        ``C:\Program Files\PostgreSQL\9.3\bin``) to your :envvar:`PATH`

      ``greenlet``, ``Pillow`` and ``lxml`` are available as pre-compiled
      wheels_ and trivially installed by pip_, ``gevent`` only needs the
      compiler to be installable and a local installation ``psycopg2``

      .. note:: by default, Python scripts are not on the PATH in windows,
                after installing pip_ add ``C:\Python27\Scripts`` to your
                :envvar:`PATH`

.. danger:: whatever the installation method, Odoo on Windows also needs
            pywin32_ which is not listed in the requirements file. It can be
            installed using pip_ with ``pip install pypiwin32``, or manually
            by downloading the official pywin32_ installer and running it.

Running Odoo
------------

Once all dependencies are set up, Odoo can be launched by running ``odoo.py``.

:ref:`Configuration <reference/cmdline>` can be provided either through
:ref:`command-line arguments <reference/cmdline>` or through a
:ref:`configuration file <reference/cmdline/config>`.

Common necessary configurations are:

* PostgreSQL host, port, user and password. Odoo has no defaults beyond
  `psycopg2's defaults <http://initd.org/psycopg/docs/module.html>`_: connects
  over a UNIX socket on port 5432 with the current user and no password.

  This may require creating new PostgreSQL roles, by default the only user is
  ``postgres``, and Odoo forbids connecting as ``postgres``.
* Custom addons path beyond the defaults, to load your own modules

.. _setup/install/vcs:

VCS Checkout
============

The VCS Checkout installation method is similar to
:ref:`source-based installation <setup/install/source>` in most respect.

* Instead of downloading a tarball the Odoo source code is downloaded from
  `the repository`_ using git_
* This simplifies the development and contributions to Odoo itself
* This also simplifies maintaining non-module patches on top of the base Odoo
  system

The primary drawback of the VCS checkout method is that it is significantly
larger than a :ref:`source install <setup/install/source>` as it contains
the entire history of the Odoo project.

.. _demo: https://demo.odoo.com
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
