=======
Modules
=======



.. _reference/module/manifest:

Manifest
========

The manifest file serves to both declare a python package as an Odoo module,
and to specify a number of module metadata.

It is a file called ``__openerp__.py`` and contains a single Python
dictionary, each dictionary key specifying a module metadatum.

::

    {
        'name': "A Module",
        'version': '1.0',
        'depends': ['base'],
        'author': "Author Name",
        'category': 'Category',
        'description': """
        Description text
        """,
        # data files always loaded at installation
        'data': [
            'mymodule_view.xml',
        ],
        # data files containing optionally loaded demonstration data
        'demo': [
            'demo_data.xml',
        ],
    }

Available manifest fields are:

``name`` (``str``, required)
    the human-readable name of the module
``version`` (``str``)
    this module's version, should follow `semantic versioning`_ rules
``description`` (``str``)
    extended description for the module, in reStructuredText
``author`` (``str``)
    name of the module author
``website`` (``str``)
    website URL for the module author
``license`` (``str``, defaults: ``AGPL-3``)
    distribution license for the module
``category`` (``str``, default: ``Uncategorized``)
    classification category within Odoo, rough business domain for the module.

    Although using `existing categories`_ is recommended, the field is
    freeform and unknown categories are created on-the-fly. Category
    hierarchies can be created using the separator ``/`` e.g. ``Foo / Bar``
    will create a category ``Foo``, a category ``Bar`` as child category of
    ``Foo``, and will set ``Bar`` as the module's category.
``depends`` (``list(str)``)
    Odoo modules which must be loaded before this one, either because this
    module uses features they create or because it alters resources they
    define.

    When a module is installed, all of its dependencies are installed before
    it. Likewise during modules loading.
``data`` (``list(str)``)
    List of data files which must always be installed or updated with the
    module. A list of paths from the module root directory
``demo`` (``list(str)``)
    List of data files which are only installed or updated in *demonstration
    mode*
``auto_install`` (``bool``, default: ``False``)
    If ``True``, this module will automatically be installed if all of its
    dependencies are installed.

    It is generally used for "link modules" implementing synergic integration
    between two otherwise independent modules.

    For instance ``sale_crm`` depends on both ``sale`` and ``crm`` and is set
    to ``auto_install``. When both ``sale`` and ``crm`` are installed, it
    automatically adds CRM campaigns tracking to sale orders without either
    ``sale`` or ``crm`` being aware of one another

.. _semantic versioning: http://semver.org
.. _existing categories:
     https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
