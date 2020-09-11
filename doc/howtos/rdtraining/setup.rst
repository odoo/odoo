.. _howto/rdtraining/setup:

==============================
Development Environment Set-up
==============================

There are multiple ways to install Odoo depending on the intended use case.

This documents attempts to describe the installation option for an internal Odoo R&D developer. We
assume that you are installing your development environment in an Odoo's standard laptop with Linux
Mint installed and updated. If you another environment is used, you can refer to :ref:`setup/install/source`

Fetch the sources & configure Git
=================================

Install and configure git
-------------------------

.. code-block:: console

    $ sudo apt install git
    $ git config --global user.name "Your full name"
    $ git config --global user.email "xyz@odoo.com"

Configure github
----------------

To fetch the sources and to contribute in the Odoo's development you will need a GitHub user. If you
don't have already a GitHub user, we will recommend using your trigram (xyz) followed by '-odoo':
'xyz-odoo'.


The easy way to authenticate to GitHub is to use the ssh connection, using the ssh authentication
will allow you to connect to GitHub without supplying your username or password at each visit.


The following instructions are based on the official `GitHub documentation`_.

.. _GitHub documentation: https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh


In your computer:


- Generating a new SSH key, adding it to the ssh-agent and copy the SSH key to your clipboard.

  .. code-block:: console

    $ ssh-keygen -t rsa -b 4096 -C "xyz@odoo.com"
    $ ssh-add ~/.ssh/id_rsa
    $ sudo apt-get install xclip
    $ xclip -sel clip < ~/.ssh/id_rsa.pub


In Github:


- In the upper-right corner of any page, click your profile photo, then click Settings

  .. image:: https://docs.github.com/assets/images/help/settings/userbar-account-settings.png

- In the user settings sidebar, click SSH and GPG keys.

  .. image:: https://docs.github.com/assets/images/help/settings/settings-sidebar-ssh-keys.png

- Click New SSH key or Add SSH key.

  .. image:: https://docs.github.com/assets/images/help/settings/ssh-add-ssh-key.png

- In the "Title" field, add a descriptive label for the new key.
- Paste your key into the "Key" field.

  .. image:: https://docs.github.com/assets/images/help/settings/ssh-key-paste.png

- Click Add SSH key.

  .. image:: https://docs.github.com/assets/images/help/settings/ssh-add-key.png


Fetch the sources
-----------------

All the Odoo sources will be located in `/home/$USER/src/`

.. code-block:: console

    $ cd /home/$USER
    $ mkdir src
    $ cd src
    $ git clone git@github.com:odoo/odoo.git
    $ git clone git@github.com:odoo/enterprise.git


.. tip:: You may need to ask your manager read rights to fetch the enterprise repository.


Configure odoo-dev
------------------

Odoo-dev is the internal R&D repository, it's in this repository that you will create your working
branches. This repository is only available if you are working at Odoo.

.. code-block:: console

    $ cd /home/$USER/src/odoo
    $ git remote add odoo-dev git@github.com:odoo-dev/odoo.git #add odoo-dev as remote
    $ git remote rename origin odoo #change the name of origin (the odoo repository) to odoo
    $ git remote set-url --push odoo no_push #remove the posibilities to push to odoo (you can only push to odoo-dev)

    $ cd /home/$USER/src/enterprise
    $ git remote add enterprise-dev git@github.com:odoo-dev/enterprise.git
    $ git remote rename origin enterprise
    $ git remote set-url --push enterprise no_push


Useful git commands
-------------------

These are useful git commands for your every working day.

* Change branch
  When you change branch, both repositories (odoo and enterprise) must be synchronized, i.e., both
  need to be in the same branch.

  .. code-block:: console

    $ cd /home/$USER/src/odoo
    $ git checkout saas-13.5

    $ cd /home/$USER/src/enterprise
    $ git checkout saas-13.5

* Fetch and rebase :

  .. code-block:: console

    $ cd /home/$USER/src/odoo
    $ git fetch --all
    $ git rebase --autostash odoo/saas-13.5

    $ cd /home/$USER/src/enterprise
    $ git fetch --all
    $ git rebase --autostash enterprise/saas-13.5


Install the dependencies
========================

Python
------

Odoo requires Python 3.6 or later, if your computer is updated you should already have an updated version.

You can check your Python version with:

.. code-block:: console

    $ python3 --version

Install pip3 and libraries
--------------------------

For libraries using native code, it is necessary to install development tools and native
dependencies before the Python dependencies of Odoo.

.. code-block:: console

    $ sudo apt install python3-pip
    $ sudo apt install python3-dev libxml2-dev libxslt1-dev libldap2-dev libsasl2-dev
    $ sudo apt install libssl-dev libpq-dev libjpeg-dev


Install odoo requirements
-------------------------

.. code-block:: console

    $ cd /home/$USER/src/odoo
    $ pip3 install -r requirements.txt


Install wkhtmltopdf
-------------------

wkhtmltopdf is a library to render HTML into PDF, it is used to create the PDF reports. wkhtmltopdf
is not installed through pip and must be installed manually in version 0.12.5 for it to support
headers and footers.

.. code-block:: console

    $ cd /tmp/
    $ sudo wget https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.5/wkhtmltox_0.12.5-1.focal_amd64.deb
    $ sudo gdebi --n wkhtmltox_0.12.5-1.focal_amd64.deb
    $ sudo ln -s /usr/local/bin/wkhtmltopdf /usr/bin
    $ sudo ln -s /usr/local/bin/wkhtmltoimage /usr/bin

Right-to-left interface support
-------------------------------

.. code-block:: console

    $ sudo apt-get install nodejs npm
    $ sudo npm install -g rtlcss

Install PostgreSQL
------------------

Odoo needs a PostgreSQL server to run properly.

.. code-block:: console

    $ sudo apt install postgresql postgresql-client
    $ sudo -u postgres createuser -s $USER


Some sql useful commands :

.. code-block:: console

    $ createdb $DB_NAME #Create a database
    $ dropdb $DB_NAME #Drop a database

    $ psql $DB_NAME #Connect into a database
        \l #List all the available databases
        \dt #List all the table of the $DB_NAME database
        \d $TABLE_NAME #Show the structure of the table $TABLE_NAME
        \q #Quit the psql environment (ctrl + d)

Run the server
==============

Running odoo-bin
----------------

Once all dependencies are set up, Odoo can be launched by running odoo-bin, the command-line interface of the server.

.. code-block:: console

    $ cd src/odoo/
    $ ./odoo-bin --addons-path="addons/,../enterprise/" -d rd-demo

There are multiples :ref:`command-line arguments <reference/cmdline/server>` that you can use to
configure the server. In this training, you will only need some of them.

* `-d <database>`
  The database that is going to be used.

* `--addons-path <directories>`
  Comma-separated list of directories in which modules are stored. These directories are scanned for
  modules.

* `--limit-time-cpu <limit>`
  Prevents the worker from using more than <limit> CPU seconds for each request.

* `--limit-time-real <limit>`
  Prevents the worker from taking longer than <limit> seconds to process a request.

The last two are going to be used to avoid killing the worker when debugging the source code.

.. tip:: If when you start the server you have an error like `AttributeError: module '$MODULE_NAME' has no attribute '$ATTRIBUTE'`

         You may need to re-install the module with `$ pip install --upgrade --force-reinstall $MODULE_NAME`

         If this error occurs with more than one module you may need to re-install all the
         requirements with `$ pip3 install --upgrade --force-reinstall -r requirements.txt`

         You can also remove the python cache to solve the issue

         .. code-block:: console

            $ cd /home/$USER/.local/lib/python3.8/site-packages/
            $ find -name '*.pyc' -type f -delete


Log in to odoo
--------------

Open `http://localhost:8069/` at your browser. We recommend you to use: Firefox, Chrome
(Chromium the open source equivalent) or any other browser with development tools.

To log in as the administrator user, you can use the following credentials : email = `admin` ;
password = `admin`.

The developer mode
==================

The Developer or Debug Mode gives you access to extra and advanced tools.

This will be useful during the whole training, for the rest of the training we will always assume
that the user is in developer mode.

To activate the developer or debug mode you can follow the steps `here`_.

.. _here: https://www.odoo.com/documentation/user/13.0/general/developer_mode/activate.html

Extra tools
===========

code editor
-----------
If you are working at Odoo, many of your colleagues are using `VSCode`_ (`VSCodium`_ the open source
equivalent), `Sublime Text`_ or `PyCharm`_. However, you are free to chose your preferred editor.

Don't forget to configure correctly the linters. Using a linter can help show syntax and semantic
warnings or errors. Odoo source code tries to respect Python and JavaScript standards, but some of
them can be ignored.

For Python, we use PEP8 with these options ignored :

- E501: line too long
- E301: expected 1 blank line, found 0
- E302: expected 2 blank lines, found 1

For JavaScript, we use ESLinter, and you can find a `configuration file example here`_.

.. _configuration file example here: https://github.com/odoo/odoo/wiki/Javascript-coding-guidelines#use-a-linter
.. _VSCode: https://code.visualstudio.com/
.. _VSCodium: https://vscodium.com/
.. _Sublime Text: https://www.sublimetext.com/
.. _PyCharm: https://www.jetbrains.com/fr-fr/pycharm/download/#section=linux

Administration tools for PostgreSQL
-----------------------------------

You can administrate your PostgreSQL databases using the command line as exemplified before or using
some GUI application as `pgAdmin`_ or `DBeaver`_.

To connect the GUI application to your database we recommend you to connect using the Unix socket.
Host name/address = /var/run/postgresql
Port = 5432
Username = $Home

.. _pgAdmin: https://www.pgadmin.org/download/pgadmin-4-apt/
.. _DBeaver: https://dbeaver.io/

Python Debugging
----------------

When you have a bug, debugging it using print might be enough at first. But, by learning how to use
a proper debugger, you will gain time.

You can use a classic Python library debugger (`pdb`_, `pudb`_ or `ipdb`_) or you can use your
editor debugger. In the beginning, to avoid difficult configurations, it's easier if you use a
library debugger.

In the following example, I'm going to use pdb, but the procedure is the same with the others ones.

- Install the library

  .. code-block:: console

        pip3 install pdb

- Trigger (breakpoint)

  .. code-block:: console

        import pdb; pdb.set_trace()

  Example:

  .. code-block:: console

        def copy(self, default=None):
            import pudb; pu.db
            self.ensure_one()
            chosen_name = default.get('name') if default else ''
            new_name = chosen_name or _('%s (copy)') % self.name
            default = dict(default or {}, name=new_name)
            return super(Partner, self).copy(default)

- Commands:

    - `h(elp) [command]`

      Without argument, print the list of available commands. With a command as argument, print help
      about that command.

    - `w(here)`

      Print a stack trace, with the most recent frame at the bottom.

    - `d(own)`

      Move the current frame one level down in the stack trace (to a newer frame).

    - `u(p)`

      Move the current frame one level up in the stack trace (to an older frame).

    - `n(ext)`

      Continue execution until the next line in the current function is reached or it returns.

    - `c(ontinue)`

      Continue execution, only stop when a breakpoint is encountered.

    - `q(uit)`

      Quit from the debugger. The program being executed is aborted.

.. tip:: To avoid killing the worker when debugging, you can add this arguments when launching the
         server ` --limit-time-cpu=9999999999 --limit-time-real=9999999999`

.. _pdb: https://docs.python.org/3/library/pdb.html
.. _pudb: https://pypi.org/project/pudb/
.. _ipdb: https://pypi.org/project/ipdb/