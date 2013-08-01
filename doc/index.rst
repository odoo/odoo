:orphan:

========================================
OpenERP Server Developers Documentation
========================================

OpenERP Server
''''''''''''''

.. toctree::
   :maxdepth: 2

   01_getting_started
   02_architecture
   03_module_dev
   04_security
   workflows
   05_test_framework
   06_misc
   deployment-gunicorn
   deployment-mod-wsgi
   form-view-guidelines
   ir_actions

OpenERP Command
'''''''''''''''

.. toctree::
   :maxdepth: 1

   openerp-command.rst
   commands.rst
   adding-command.rst

OpenERP Server API
''''''''''''''''''

.. toctree::
   :maxdepth: 1

   orm-methods.rst
   api_models.rst
   routing.rst

Changelog
'''''''''

.. toctree::
   :maxdepth: 1

   changelog.rst

Concepts
''''''''

.. glossary::

    Database ID

        The primary key of a record in a PostgreSQL table (or a
        virtual version thereof), usually varies from one database to
        the next.

    External ID
