:orphan:

========================================
OpenERP Server Developers Documentation
========================================

Howto
'''''

.. toctree::
    :maxdepth: 1

    howto/howto_website

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

OpenERP Server API
''''''''''''''''''

.. toctree::
   :maxdepth: 1

   new_api
   orm-methods
   api_models
   routing

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
