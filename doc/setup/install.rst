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
be downloaded from our download_ page (you must to be logged in as a paying
customer or partner to download the Enterprise packages).

Windows
-------

#. Download the installer from our nightly_ server (Community only) or the Windows installer from
   the download_ page (any edition).
#. Execute the downloaded file.

   .. warning:: | On Windows 8 and later you may see a warning titled "Windows protected your PC".
                | Click on **More Info** and then on **Run anyway**.

#. Accept the UAC_ prompt.
#. Go through the various installation steps.

Odoo will automatically be started at the end of the installation.

Linux
-----

Debian/Ubuntu
'''''''''''''

Odoo 13.0 'deb' package currently supports `Debian Buster`_, `Ubuntu 18.04`_ or above.

Prepare
^^^^^^^

Odoo needs a `PostgreSQL`_ server to run properly. The default configuration for
the Odoo 'deb' package is to use the PostgreSQL server on the same host as your
Odoo instance. Execute the following command in order to install the PostgreSQL server:

.. code-block:: console

  $ sudo apt install postgresql -y

.. warning:: `wkhtmltopdf` is not installed through **pip** and must be installed manually in
             version `0.12.5 <the wkhtmltopdf download page_>`_ for it to support headers and
             footers. See our `wiki <https://github.com/odoo/odoo/wiki/Wkhtmltopdf>`_ for more
             details on the various versions.

Repository
^^^^^^^^^^

Odoo S.A. provides a repository that can be used with  Debian and Ubuntu distributions. It can be
used to install *Odoo Community Edition* by executing the following commands **as root**:

.. code-block:: console

    # wget -O - https://nightly.odoo.com/odoo.key | apt-key add -
    # echo "deb http://nightly.odoo.com/14.0/nightly/deb/ ./" >> /etc/apt/sources.list.d/odoo.list
    # apt-get update && apt-get install odoo

You can then use the usual `apt-get upgrade` command to keep your installation up-to-date.

At this moment, there is no nightly repository for the Enterprise Edition.

Deb Package
^^^^^^^^^^^

Instead of using the repository as described above, the 'deb' packages for both the *Community* and
*Enterprise* editions can be downloaded from the `official download page <download_>`_.

Next, execute the following commands **as root**:

.. code-block:: console

    # dpkg -i <path_to_installation_package> # this probably fails with missing dependencies
    # apt-get install -f # should install the missing dependencies
    # dpkg -i <path_to_installation_package>

This will install Odoo as a service, create the necessary PostgreSQL_ user
and automatically start the server.

.. warning:: The `python3-xlwt` Debian package does not exists in Debian Buster nor Ubuntu 18.04.
             This python module is needed to export into xls format.

             If you need the feature, you can install it manually with:

             .. code-block:: console

                $ sudo pip3 install xlwt

.. warning:: The `num2words` python package does not exists in Debian Buster nor Ubuntu 18.04.
             Textual amounts will not be rendered by Odoo and this could cause problems with the
             `l10n_mx_edi` module.

             If you need this feature, you can install manually with:

             .. code-block:: console

                $ sudo pip3 install num2words

Fedora
''''''

Odoo 13.0 'rpm' package supports Fedora 30.

Prepare
^^^^^^^
Odoo needs a `PostgreSQL`_ server to run properly. Make sure that the `sudo` command is available
and well configured and, only then, execute the following command in order to install the PostgreSQL
server:

.. code-block:: console

    $ sudo dnf install -y postgresql-server
    $ sudo postgresql-setup --initdb --unit postgresql
    $ sudo systemctl enable postgresql
    $ sudo systemctl start postgresql

.. warning:: `wkhtmltopdf` is not installed through **pip** and must be installed manually in
             version `0.12.5 <the wkhtmltopdf download page_>`_ for it to support headers and
             footers. See our `wiki <https://github.com/odoo/odoo/wiki/Wkhtmltopdf>`_ for more
             details on the various versions.

Repository
^^^^^^^^^^

Odoo S.A. provides a repository that can be used with the Fedora distributions.
It can be used to install *Odoo Community Edition* by executing the following
commands:

.. code-block:: console

    $ sudo dnf config-manager --add-repo=https://nightly.odoo.com/14.0/nightly/rpm/odoo.repo
    $ sudo dnf install -y odoo
    $ sudo systemctl enable odoo
    $ sudo systemctl start odoo

RPM package
^^^^^^^^^^^

Instead of using the repository as described above, the 'rpm' packages for both the *Community* and
*Enterprise* editions can be downloaded from the `official download page <download_>`_.

Once downloaded, the package can be installed using the 'dnf' package manager:

.. code-block:: console

    $ sudo dnf localinstall odoo_13.0.latest.noarch.rpm
    $ sudo systemctl enable odoo
    $ sudo systemctl start odoo


.. _setup/install/source:

Source Install
==============

The source "installation" is really about not installing Odoo, and running it directly from source
instead.

This can be more convenient for module developers as the Odoo source is more easily accessible
than using packaged installation (for information or to build this documentation and have it
available offline).

It also makes starting and stopping Odoo more flexible and explicit than the services set up by the
packaged installations, and allows overriding settings using
:ref:`command-line parameters <reference/cmdline>` without needing to edit a configuration file.

Finally it provides greater control over the system's set up, and allows to more easily keep
(and run) multiple versions of Odoo side-by-side.

Windows
-------

Fetch the sources
'''''''''''''''''

There are two ways to obtain the source code of Odoo: as a zip **archive** or through **git**.

Archive
^^^^^^^

Community Edition:

* `Official download page <download_>`_
* `GitHub repository <community-repository_>`_
* `Nightly server <nightly_>`_

Enterprise Edition:

* `Official download page <download_>`_
* `GitHub repository <enterprise-repository_>`_

Git
^^^

The following requires git_ to be installed on your machine and that you have basic knowledge of
git commands.

Community Edition:

.. code-block:: doscon

    C:\> git clone https://github.com/odoo/odoo.git


Enterprise Edition: (see :ref:`setup/install/editions` to get access)

.. code-block:: doscon

  C:\> git clone https://github.com/odoo/enterprise.git

.. note:: **The Enterprise git repository does not contain the full Odoo source code**. It is only
          a collection of extra add-ons. The main server code is in the Community version. Running
          the Enterprise version actually means running the server from the Community version with
          the addons-path option set to the folder with the Enterprise version. You need to clone
          both the Community and Enterprise repository to have a working Odoo Enterprise
          installation.

Prepare
'''''''

Python
^^^^^^

Odoo requires Python 3.6 or later to run. Visit `Python's download page <https://www.python.org/downloads/windows/>`_
to download and install the latest version of Python 3 on your machine.

During installation, check **Add Python 3 to PATH**, then click **Customize Installation** and make
sure that **pip** is checked.

.. note:: If Python 3 is already installed, make sure that the version is 3.6 or above, as previous
          versions are not compatible with Odoo.

          .. code-block:: doscon

              C:\> python --version

          Verify also that pip_ is installed for this version.

          .. code-block:: doscon

              C:\> pip --version

PostgreSQL
^^^^^^^^^^

Odoo uses PostgreSQL as database management system. `Download and install PostgreSQL <https://www.postgresql.org/download/windows/>`_
(supported version: 10.0 and later).

By default, the only user is `postgres` but Odoo forbids connecting as `postgres`, so you need to
create a new PostgreSQL user:

#. Add PostgreSQL's `bin` directory (by default: `C:\\Program Files\\PostgreSQL\\<version>\\bin`) to
   your `PATH`.
#. Create a postgres user with a password using the pg admin gui:

   1. Open **pgAdmin**.
   2. Double-click the server to create a connection.
   3. Select :menuselection:`Object --> Create --> Login/Group Role`.
   4. Enter the username in the **Role Name** field (e.g. `odoo`).
   5. Open the **Definition** tab and enter the password (e.g. ``odoo``), then click **Save**.
   6. Open the **Privileges** tab and switch **Can login?** to `Yes` and **Create database?** to
      `Yes`.

Dependencies
^^^^^^^^^^^^

Before installing the dependencies, you must download and install the
`Build Tools for Visual Studio <https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019>`_.
When prompted, select **C++ build tools** in the **Workloads** tab and install them.

Odoo dependencies are listed in the `requirements.txt` file located at the root of the Odoo
community directory.

.. tip:: It can be preferable to not mix python modules packages between different instances of Odoo
         or with your system. You can use virtualenv_ to create isolated Python environments.

Navigate to the path of your Odoo Community installation (`CommunityPath`) and run **pip**
on the requirements file in a terminal **with Administrator privileges**:

.. code-block:: doscon

    C:\> cd \CommunityPath
    C:\> pip install setuptools wheel
    C:\> pip install -r requirements.txt

.. warning:: `wkhtmltopdf` is not installed through **pip** and must be installed manually in
             version `0.12.5 <the wkhtmltopdf download page_>`_ for it to support headers and
             footers. See our `wiki <https://github.com/odoo/odoo/wiki/Wkhtmltopdf>`_ for more
             details on the various versions.

For languages with right-to-left interface (such as Arabic or Hebrew), the package `rtlcss` is
needed:

#. Download and install `nodejs <https://nodejs.org/en/download/>`_.
#. Install `rtlcss`:

   .. code-block:: doscon

       C:\> npm install -g rtlcss

#. Edit the System Environment's variable `PATH` to add the folder where `rtlcss.cmd` is located
   (typically: `C:\\Users\\<user>\\AppData\\Roaming\\npm\\`).

Running Odoo
''''''''''''

Once all dependencies are set up, Odoo can be launched by running `odoo-bin`, the
command-line interface of the server. It is located at the root of the Odoo Community directory.

To configure the server, you can either specify :ref:`command-line arguments <reference/cmdline/server>` or a
:ref:`configuration file <reference/cmdline/config>`.

.. tip:: For the Enterprise edition, you must add the path to the `enterprise` addons to the
         `addons-path` argument. Note that it must come before the other paths in `addons-path` for
         addons to be loaded correctly.

Common necessary configurations are:

* PostgreSQL user and password.
* Custom addon paths beyond the defaults, to load your own modules.

A typical way to run the server would be:

.. code-block:: doscon

    C:\> cd CommunityPath/
    C:\> python odoo-bin -r dbuser -w dbpassword --addons-path=addons -d mydb

Where `CommunityPath` is the path of the Odoo Community installation, `dbuser` is the
PostgreSQL login, `dbpassword` is the PostgreSQL password
and `mydb` is the default database to serve on `localhost:8069`. You can add other
directory paths separated by a comma to ``addons`` at the end of the addons-path option.

Linux
-----

Fetch the sources
'''''''''''''''''

There are two ways to obtain the source code of Odoo: as a zip **archive** or through **git**.

Archive
^^^^^^^

Community Edition:

* `Official download page <download_>`_
* `GitHub repository <community-repository_>`_
* `Nightly server <nightly_>`_

Enterprise Edition:

* `Official download page <download_>`_
* `GitHub repository <enterprise-repository_>`_

Git
^^^

The following requires git_ to be installed on your machine and that you have basic knowledge of
git commands.

Community Edition:

.. code-block:: console

    $ git clone https://github.com/odoo/odoo.git


Enterprise Edition: (see :ref:`setup/install/editions` to get access)

.. code-block:: console

  $ git clone https://github.com/odoo/enterprise.git

.. note:: **The Enterprise git repository does not contain the full Odoo source code**. It is only
          a collection of extra add-ons. The main server code is in the Community version. Running
          the Enterprise version actually means running the server from the Community version with
          the addons-path option set to the folder with the Enterprise version. You need to clone
          both the Community and Enterprise repository to have a working Odoo Enterprise
          installation.

Prepare
'''''''

Python
^^^^^^

Odoo requires Python 3.6 or later to run. Use your package manager to download and install Python 3
on your machine if it is not already done.

.. note:: If Python 3 is already installed, make sure that the version is 3.6 or above, as previous
          versions are not compatible with Odoo.

          .. code-block:: console

              $ python3 --version

          Verify also that pip_ is installed for this version.

          .. code-block:: console

              $ pip3 --version

PostgreSQL
^^^^^^^^^^

Odoo uses PostgreSQL as database management system. Use your package manager to download and install
PostgreSQL (supported version: 10.0 and later).

On Debian/Unbuntu, it can be achieved by executing the following:

.. code-block:: console

    $ sudo apt install postgresql postgresql-client

By default, the only user is `postgres` but Odoo forbids connecting as `postgres`, so you need to
create a new PostgreSQL user:

.. code-block:: console

  $ sudo -u postgres createuser -s $USER
  $ createdb $USER

.. note:: Because your PostgreSQL user has the same name as your Unix login, you will be able to
          connect to the database without password.

Dependencies
^^^^^^^^^^^^

For libraries using native code, it is necessary to install development tools and native
dependencies before the Python dependencies of Odoo. They are available in `-dev` or `-devel`
packages for Python, PostgreSQL, libxml2, libxslt1, libevent, libsasl2 and libldap2.

On Debian/Unbuntu, the following command should install all the required libraries:

.. code-block:: console

    $ sudo apt install python3-dev libxml2-dev libxslt1-dev libldap2-dev libsasl2-dev \
        libtiff5-dev libjpeg8-dev libopenjp2-7-dev zlib1g-dev libfreetype6-dev \
        liblcms2-dev libwebp-dev libharfbuzz-dev libfribidi-dev libxcb1-dev libpq-dev

Odoo dependencies are listed in the `requirements.txt` file located at the root of the Odoo
community directory.

.. tip:: It can be preferable to not mix python modules packages between different instances of Odoo
         or with your system. You can use virtualenv_ to create isolated Python environments.

Navigate to the path of your Odoo Community installation (`CommunityPath`) and run **pip**
on the requirements file:

.. code-block:: console

    $ cd /CommunityPath
    $ pip3 install setuptools wheel
    $ pip3 install -r requirements.txt

.. warning:: `wkhtmltopdf` is not installed through **pip** and must be installed manually in
             version `0.12.5 <the wkhtmltopdf download page_>`_ for it to support headers and
             footers. See our `wiki <https://github.com/odoo/odoo/wiki/Wkhtmltopdf>`_ for more
             details on the various versions.

For languages with right-to-left interface (such as Arabic or Hebrew), the package `rtlcss` is
needed:

#. Download and install **nodejs** and **npm** with your package manager.
#. Install `rtlcss`:

   .. code-block:: console

       $ sudo npm install -g rtlcss

Running Odoo
''''''''''''

Once all dependencies are set up, Odoo can be launched by running `odoo-bin`, the
command-line interface of the server. It is located at the root of the Odoo Community directory.

To configure the server, you can either specify :ref:`command-line arguments <reference/cmdline/server>` or a
:ref:`configuration file <reference/cmdline/config>`.

.. tip:: For the Enterprise edition, you must add the path to the `enterprise` addons to the
         `addons-path` argument. Note that it must come before the other paths in `addons-path` for
         addons to be loaded correctly.

Common necessary configurations are:

* PostgreSQL user and password. Odoo has no defaults beyond
  `psycopg2's defaults <http://initd.org/psycopg/docs/module.html>`_: connects over a UNIX socket on
  port `5432` with the current user and no password.
* Custom addon paths beyond the defaults, to load your own modules.

A typical way to run the server would be:

.. code-block:: console

    $ cd /CommunityPath
    $ python3 odoo-bin --addons-path=addons -d mydb

Where `CommunityPath` is the path of the Odoo Community installation
and `mydb` is the default database to serve on `localhost:8069`. You can add other
directory paths separated by a comma to ``addons`` at the end of the addons-path option.

Mac OS
------

Fetch the sources
'''''''''''''''''

There are two ways to obtain the source code of Odoo: as a zip **archive** or through **git**.

Archive
^^^^^^^

Community Edition:

* `Official download page <download_>`_
* `GitHub repository <community-repository_>`_
* `Nightly server <nightly_>`_

Enterprise Edition:

* `Official download page <download_>`_
* `GitHub repository <enterprise-repository_>`_

Git
^^^

The following requires git_ to be installed on your machine and that you have basic knowledge of
git commands.

Community Edition:

.. code-block:: console

    $ git clone https://github.com/odoo/odoo.git


Enterprise Edition: (see :ref:`setup/install/editions` to get access)

.. code-block:: console

  $ git clone https://github.com/odoo/enterprise.git

.. note:: **The Enterprise git repository does not contain the full Odoo source code**. It is only
          a collection of extra add-ons. The main server code is in the Community version. Running
          the Enterprise version actually means running the server from the Community version with
          the addons-path option set to the folder with the Enterprise version. You need to clone
          both the Community and Enterprise repository to have a working Odoo Enterprise
          installation.

Prepare
'''''''

Python
^^^^^^

Odoo requires Python 3.6 or later to run. Use your preferred package manager (homebrew_, macports_)
to download and install Python 3 on your machine if it is not already done.

.. note:: If Python 3 is already installed, make sure that the version is 3.6 or above, as previous
          versions are not compatible with Odoo.

          .. code-block:: console

              $ python3 --version

          Verify also that pip_ is installed for this version.

          .. code-block:: console

              $ pip3 --version

PostgreSQL
^^^^^^^^^^

Odoo uses PostgreSQL as database management system. Use `postgres.app <https://postgresapp.com>`_
to download and install PostgreSQL (supported version: 10.0 and later).

By default, the only user is `postgres` but Odoo forbids connecting as `postgres`, so you need to
create a new PostgreSQL user:

.. code-block:: console

  $ sudo -u postgres createuser -s $USER
  $ createdb $USER

.. note:: Because your PostgreSQL user has the same name as your Unix login, you will be able to
          connect to the database without password.

Dependencies
^^^^^^^^^^^^

Odoo dependencies are listed in the `requirements.txt` file located at the root of the Odoo
community directory.

.. tip:: It can be preferable to not mix python modules packages between different instances of Odoo
         or with your system. You can use virtualenv_ to create isolated Python environments.

Navigate to the path of your Odoo Community installation (`CommunityPath`) and run **pip**
on the requirements file:

.. code-block:: console

   $ cd /CommunityPath
   $ pip3 install setuptools wheel
   $ pip3 install -r requirements.txt

.. warning:: Non-Python dependencies need to be installed with a package manager:

             #. Download and install the **Command Line Tools**:

                .. code-block:: console

                   $ xcode-select --install

             #. Download and install the package manager of your choice (homebrew_, macports_).
             #. Install non-python dependencies.

.. warning:: `wkhtmltopdf` is not installed through **pip** and must be installed manually in
             version `0.12.5 <the wkhtmltopdf download page_>`_ for it to support headers and
             footers. See our `wiki <https://github.com/odoo/odoo/wiki/Wkhtmltopdf>`_ for more
             details on the various versions.

For languages with right-to-left interface (such as Arabic or Hebrew), the package `rtlcss` is
needed:

#. Download and install **nodejs** with your preferred package manager (homebrew_, macports_).
#. Install `rtlcss`:

   .. code-block:: console

       $ sudo npm install -g rtlcss

Running Odoo
''''''''''''

Once all dependencies are set up, Odoo can be launched by running `odoo-bin`, the
command-line interface of the server. It is located at the root of the Odoo Community directory.

To configure the server, you can either specify :ref:`command-line arguments <reference/cmdline/server>` or a
:ref:`configuration file <reference/cmdline/config>`.

.. tip:: For the Enterprise edition, you must add the path to the `enterprise` addons to the
         `addons-path` argument. Note that it must come before the other paths in `addons-path` for
         addons to be loaded correctly.

Common necessary configurations are:

* PostgreSQL user and password. Odoo has no defaults beyond
  `psycopg2's defaults <http://initd.org/psycopg/docs/module.html>`_: connects over a UNIX socket on
  port `5432` with the current user and no password.
* Custom addon paths beyond the defaults, to load your own modules.

A typical way to run the server would be:

.. code-block:: console

    $ cd /CommunityPath
    $ python3 odoo-bin --addons-path=addons -d mydb

Where `CommunityPath` is the path of the Odoo Community installation
and `mydb` is the default database to serve on `localhost:8069`. You can add other
directory paths separated by a comma to ``addons`` at the end of the addons-path option.


.. _setup/install/docker:

Docker
======

The full documentation on how to use Odoo with Docker can be found on the
official Odoo `docker image <https://registry.hub.docker.com/_/odoo/>`_ page.

.. _Debian Buster: https://www.debian.org/releases/buster/
.. _demo: https://demo.odoo.com
.. _docker: https://www.docker.com
.. _download: https://www.odoo.com/page/download
.. _Ubuntu 18.04: http://releases.ubuntu.com/18.04/
.. _EPEL: https://fedoraproject.org/wiki/EPEL
.. _PostgreSQL: http://www.postgresql.org
.. _the official installer:
.. _install pip:
    https://pip.pypa.io/en/latest/installing.html#install-pip
.. _Quilt: http://en.wikipedia.org/wiki/Quilt_(software)
.. _saas: https://www.odoo.com/page/start
.. _the wkhtmltopdf download page: https://github.com/wkhtmltopdf/wkhtmltopdf/releases/tag/0.12.5
.. _UAC: http://en.wikipedia.org/wiki/User_Account_Control
.. _wkhtmltopdf: http://wkhtmltopdf.org
.. _pip: https://pip.pypa.io
.. _macports: https://www.macports.org
.. _homebrew: http://brew.sh
.. _wheels: https://wheel.readthedocs.org/en/latest/
.. _virtualenv: https://pypi.python.org/pypi/virtualenv
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/en/latest/
.. _pywin32: http://sourceforge.net/projects/pywin32/files/pywin32/
.. _community-repository: https://github.com/odoo/odoo
.. _enterprise-repository: https://github.com/odoo/enterprise
.. _git: https://git-scm.com/
.. _Editions: https://www.odoo.com/pricing#pricing_table_features
.. _nightly: https://nightly.odoo.com/
.. _extra: https://nightly.odoo.com/extra/
