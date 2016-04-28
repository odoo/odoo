:banner: banners/odoo_guideline.jpg

.. highlight:: python

===============
Odoo Guidelines
===============

This page introduce the new Odoo Coding Guidelines. These guidelines
aim to improve the quality of the code (better readability of source,
...) and  Odoo Apps. Indeed, proper code ought ease maintenance, aid
debugging, lower complexity and promote reliability.

.. warning::

    These guidelines are written with new modules and new files in mind. When
    modifying existing files, the original style of the file strictly supersedes
    any other style guidelines. In other words, never modify existing files in
    order to apply these guidelines, to avoid disrupting the revision history of
    each line. For more details, see our `pull request guide <https://odoo.com/submit-pr>`_.

Module structure
================

Directories
-----------
A module is organised in a few directories :

- *data/* : demo and data xml
- *models/* : models definition
- *controllers/* : contains controllers (http routes).
- *views/* : contains the views and templates
- *static/* : contains the web assets, separated into *css/, js/, img/, lib/, ...*

File naming
-----------
For *views* declarations, split backend views from (frontend)
templates in 2 differents files.

For *models*, split the business logic by sets of models, in each set
select a main model, this model gives its name to the set. If there is
only one model, its name is the same as the module name. For
each set named <main_model> the following files may be created:

- :file:`models/{<main_model>}.py`
- :file:`models/{<inherited_main_model>}.py`
- :file:`views/{<main_model>}_templates.xml`
- :file:`views/{<main_model>}_views.xml`

For instance, *sale* module introduces ``sale_order`` and
``sale_order_line`` where ``sale_order`` is dominant. So the
``<main_model>`` files will be named :file:`models/sale_order.py` and
:file:`views/sale_order_views.py`.


For *data*, split them by purpose : demo or data. The filename will be
the main_model name, suffixed by *_demo.xml* or *_data.xml*.

For *controller*, the only file should be named *main.py*.

For *static files*, the name pattern is *<module_name>.ext* (i.e. :
static/js/im_chat.js, static/css/im_chat.css, static/xml/im_chat.xml,
...). Don't link data (image, libraries) outside Odoo : don't use an
url to an image but copy it in our codebase instead.

The complete tree should look like

.. code-block:: text

    addons/<my_module_name>/
    |-- __init__.py
    |-- __openerp__.py
    |-- controllers/
    |   |-- __init__.py
    |   `-- main.py
    |-- data/
    |   |-- <main_model>_data.xml
    |   `-- <inherited_main_model>_demo.xml
    |-- models/
    |   |-- __init__.py
    |   |-- <main_model>.py
    |   `-- <inherited_main_model>.py
    |-- security/
    |   |-- ir.model.access.csv
    |   `-- <main_model>_security.xml
    |-- static/
    |   |-- img/
    |   |   |-- my_little_kitten.png
    |   |   `-- troll.jpg
    |   |-- lib/
    |   |   `-- external_lib/
    |   `-- src/
    |       |-- js/
    |       |   `-- <my_module_name>.js
    |       |-- css/
    |       |   `-- <my_module_name>.css
    |       |-- less/
    |       |   `-- <my_module_name>.less
    |       `-- xml/
    |           `-- <my_module_name>.xml
    `-- views/
        |-- <main_model>_templates.xml
        |-- <main_model>_views.xml
        |-- <inherited_main_model>_templates.xml
        `-- <inherited_main_model>_views.xml


.. note:: File names should only contain ``[a-z0-9_]`` (lowercase
          alphanumerics and ``_``)

.. warning:: Use correct file permissions : folder 755 and file 644.

XML files
=========

Format
------
When declaring a record in XML,

- Place ``id`` attribute before ``model``
- For field declaration, ``name`` attribute is first. Then place the
  *value* either in the ``field`` tag, either in the ``eval``
  attribute, and finally other attributes (widget, options, ...)
  ordered by importance.

- Try to group the record by model. In case of dependencies between
  action/menu/views, the convention may not be applicable.
- Use naming convention defined at the next point
- The tag *<data>* is only used to set not-updatable data with ``noupdate=1``

.. code-block:: xml

    <record id="view_id" model="ir.ui.view">
        <field name="name">view.name</field>
        <field name="model">object_name</field>
        <field name="priority" eval="16"/>
        <field name="arch" type="xml">
            <tree>
                <field name="my_field_1"/>
                <field name="my_field_2" string="My Label" widget="statusbar" statusbar_visible="draft,sent,progress,done" />
            </tree>
        </field>
    </record>


Naming xml_id
-------------

Security, View and Action
~~~~~~~~~~~~~~~~~~~~~~~~~

Use the following pattern :

* For a menu: :samp:`{<model_name>}_menu`
* For a view: :samp:`{<model_name>}_view_{<view_type>}`, where *view_type* is
  ``kanban``, ``form``, ``tree``, ``search``, ...
* For an action: the main action respects :samp:`{<model_name>}_action`.
  Others are suffixed with :samp:`_{<detail>}`, where *detail* is a
  lowercase string briefly explaining the action.
  This is used only if multiple actions are declared for the
  model.
* For a group: :samp:`{<model_name>}_group_{<group_name>}` where *group_name*
  is the name of the group, generally 'user', 'manager', ...
* For a rule: :samp:`{<model_name>}_rule_{<concerned_group>}` where
  *concerned_group* is the short name of the concerned group ('user'
  for the 'model_name_group_user', 'public' for public user, 'company'
  for multi-company rules, ...).

.. code-block:: xml

    <!-- views and menus -->
    <record id="model_name_menu" model="ir.ui.menu">
        ...
    </record>

    <record id="model_name_view_form" model="ir.ui.view">
        ...
    </record>

    <record id="model_name_view_kanban" model="ir.ui.view">
        ...
    </record>

    <!-- actions -->
    <record id="model_name_action" model="ir.actions.act_window">
        ...
    </record>

    <record id="model_name_action_child_list" model="ir.actions.act_window">
        ...
    </record>

    <!-- security -->
    <record id="model_name_group_user" model="res.groups">
        ...
    </record>

    <record id="model_name_rule_public" model="ir.rule">
        ...
    </record>

    <record id="model_name_rule_company" model="ir.rule">
        ...
    </record>



.. note:: View names use dot notation ``my.model.view_type`` or
          ``my.model.view_type.inherit`` instead of *"This is the form view of
          My Model"*.


Inherited XML
~~~~~~~~~~~~~

The naming pattern of inherited view is
:samp:`{<base_view>}_inherit_{<current_module_name>}`. A module may only
extend a view once.  Suffix the orginal name with
:samp:`_inherit_{<current_module_name>}` where *current_module_name* is the
technical name of the module extending the view.


.. code-block:: xml

    <record id="inherited_model_view_form_inherit_my_module" model="ir.ui.view">
        ...
    </record>


Python
======

PEP8 options
------------

Using a linter can help show syntax and semantic warnings or errors. Odoo
source code tries to respect Python standard, but some of them can be ignored.

- E501: line too long
- E301: expected 1 blank line, found 0
- E302: expected 2 blank lines, found 1
- E126: continuation line over-indented for hanging indent
- E123: closing bracket does not match indentation of opening bracket's line
- E127: continuation line over-indented for visual indent
- E128: continuation line under-indented for visual indent
- E265: block comment should start with '# '

Imports
-------
The imports are ordered as

#. External libraries (one per line sorted and split in python stdlib)
#. Imports of ``openerp``
#. Imports from Odoo modules (rarely, and only if necessary)

Inside these 3 groups, the imported lines are alphabetically sorted.

.. code-block:: python

    # 1 : imports of python lib
    import base64
    import re
    import time
    # 2 :  imports of openerp
    import openerp
    from openerp import api, fields, models # alphabetically ordered
    from openerp.tools.safe_eval import safe_eval as eval
    from openerp.tools.translate import _
    # 3 :  imports from odoo modules
    from openerp.addons.website.models.website import slug
    from openerp.addons.web.controllers.main import login_redirect


Idioms
------

- Prefer ``%`` over ``.format()``, prefer ``%(varname)`` instead of position (This is better for translations)
- Try to avoid generators and decorators
- Always favor *Readability* over *conciseness* or using the language features or idioms.
- Use list comprehension, dict comprehension, and basic manipulation using ``map``, ``filter``, ``sum``, ... They make the code easier to read.
- The same applies for recordset methods : use ``filtered``, ``mapped``, ``sorted``, ...
- Each python file should have ``# coding: utf-8 `` as first line
- Use the ``UserError`` defined in ``openerp.exceptions`` instead of overriding ``Warning``, or find a more appropriate exception in *exceptions.py*
- Document your code (docstring on methods, simple comments for the tricky part of the code)
- Use meaningful variable/class/method names



Symbols
-------

- Odoo Python Class : use camelcase for code in api v8, underscore lowercase notation for old api.

.. code-block:: python

    class AccountInvoice(models.Model):
        ...

    class account_invoice(osv.osv):
        ...

- Variable name :
    - use camelcase for model variable
    - use underscore lowercase notation for common variable.
    - since new API works with record or recordset instead of id list, don't suffix variable name with *_id* or *_ids* if they not contain id or list of id.

.. code-block:: python

    ResPartner = self.env['res.partner']
    partners = ResPartner.browse(ids)
    partner_id = partners[0].id

- ``One2Many`` and ``Many2Many`` fields should always have *_ids* as suffix (example: sale_order_line_ids)
- ``Many2One`` fields should have *_id* as suffix (example : partner_id, user_id, ...)
- Method conventions
    - Compute Field : the compute method pattern is *_compute_<field_name>*
    - Search method : the search method pattern is *_search_<field_name>*
    - Default method : the default method pattern is *_default_<field_name>*
    - Onchange method : the onchange method pattern is *_onchange_<field_name>*
    - Constraint method : the constraint method pattern is *_check_<constraint_name>*
    - Action method : an object action method is prefix with *action_*. Its decorator is ``@api.multi``, but since it use only one record, add ``self.ensure_one()`` at the beginning of the method.

- In a Model attribute order should be
    #. Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    #. Default method and ``_default_get``
    #. Field declarations
    #. Compute and search methods in the same order as field declaration
    #. Constrains methods (``@api.constrains``) and onchange methods (``@api.onchange``)
    #. CRUD methods (ORM overrides)
    #. Action methods
    #. And finally, other business methods.

.. code-block:: python

    class Event(models.Model):
        # Private attributes
        _name = 'event.event'
        _description = 'Event'

        # Default methods
        def _default_name(self):
            ...

        # Fields declaration
        name = fields.Char(string='Name', default=_default_name)
        seats_reserved = fields.Integer(oldname='register_current', string='Reserved Seats',
            store=True, readonly=True, compute='_compute_seats')
        seats_available = fields.Integer(oldname='register_avail', string='Available Seats',
            store=True, readonly=True, compute='_compute_seats')
        price = fields.Integer(string='Price')

        # compute and search fields, in the same order that fields declaration
        @api.multi
        @api.depends('seats_max', 'registration_ids.state', 'registration_ids.nb_register')
        def _compute_seats(self):
            ...

        # Constraints and onchanges
        @api.constrains('seats_max', 'seats_available')
        def _check_seats_limit(self):
            ...

        @api.onchange('date_begin')
        def _onchange_date_begin(self):
            ...

        # CRUD methods
        def create(self):
            ...

        # Action methods
        @api.multi
        def action_validate(self):
            self.ensure_one()
            ...

        # Business methods
        def mail_user_confirm(self):
            ...


Javascript and CSS
==================
**For javascript :**

- ``use strict;`` is recommended for all javascript files
- Use a linter (jshint, ...)
- Never add minified Javascript Libraries
- Use camelcase for class declaration

**For CSS :**

- Prefix all your class with *o_<module_name>* where *module_name* is the technical name of the module ('sale', 'im_chat', ...) or the main route reserved by the module (for website module mainly, i.e. : 'o_forum' for website_forum module). The only exception for this rule is the webclient : it simply use *o_* prefix.
- Avoid using id
- Use bootstrap native class
- Use underscore lowercase notation to name class

Git
===

Commit message
--------------

Prefix your commit with

- **[IMP]** for improvements
- **[FIX]** for bug fixes
- **[REF]** for refactoring
- **[ADD]** for adding new resources
- **[REM]** for removing of resources
- **[MERGE]** for merge commits (only for forward/back-port)
- **[CLA]** for signing the Odoo Individual Contributor License

Then, in the message itself, specify the part of the code impacted by your changes (module name, lib, transversal object, ...) and a description of the changes.

- Always include a meaningful commit message: it should be self explanatory
  (long enough) including the name of the module that has been changed and the
  reason behind the change. Do not use single words like "bugfix" or
  "improvements".
- Avoid commits which simultaneously impact multiple modules. Try to
  split into different commits where impacted modules are different
  (It will be helpful if we need to revert a module separately).

.. code-block:: text

    [FIX] website, website_mail: remove unused alert div, fixes look of input-group-btn

    Bootstrap's CSS depends on the input-group-btn
    element being the first/last child of its parent.
    This was not the case because of the invisible
    and useless alert.

    [IMP] fields: reduce memory footprint of list/set field attributes

    [REF] web: add module system to the web client

    This commit introduces a new module system for the javascript code.
    Instead of using global ...


.. note:: Use the long description to explain the *why* not the
          *what*, the *what* can be seen in the diff
