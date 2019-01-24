:banner: banners/odoo_guideline.jpg

.. highlight:: python

===============
Odoo Guidelines
===============

This page introduces the Odoo Coding Guidelines. Those aim to improve the
quality of Odoo Apps code. Indeed proper code improves readability, eases
maintenance, helps debugging, lowers complexity and promotes reliability.
These guidelines should be applied to every new module and to all new development.

.. warning::

    When modifying existing files in **stable version** the original file style
    strictly supersedes any other style guidelines. In other words please never
    modify existing files in order to apply these guidelines. It avoids disrupting
    the revision history of code lines. Diff should be kept minimal. For more
    details, see our `pull request guide <https://odoo.com/submit-pr>`_.

.. warning::

    When modifying existing files in **master (development) version** apply those
    guidelines to existing code only for modified code or if most of the file is
    under revision. In other words modify existing files structure only if it is
    going under major changes. In that case first do a **move** commit then apply
    the changes related to the feature.

Module structure
================

Directories
-----------
A module is organized in important directories. Those contain the business logic;
having a look at them should make you understand the purpose of the module.

- *data/* : demo and data xml
- *models/* : models definition
- *controllers/* : contains controllers (HTTP routes)
- *views/* : contains the views and templates
- *static/* : contains the web assets, separated into *css/, js/, img/, lib/, ...*

Other optional directories compose the module.

- *wizard/* : regroups the transient models (``models.TransientModel``) and their views
- *report/* : contains the printable reports and models based on SQL views. Python objects and XML views are included in this directory
- *tests/* : contains the Python tests
- *security/* : contains the access rules to the module content

File naming
-----------

File naming is important to quickly find information through all odoo addons.
This section explains how to name files in a standard odoo module. As an
example we use a plant nursery application. It holds two main models plant.nursery
and plant.order.

Concerning *models*, split the business logic by sets of models belonging to
a same main model. Each set lies in a given file named based on its main model.
If there is only one model, its name is the same as the module name. Each
inherited model should be in its own file to help understanding of impacted
models.

.. code-block:: text

    addons/plant_nursery/
    |-- models/
    |   |-- plant_nursery.py (first main model)
    |   |-- plant_order.py (another main model)
    |   |-- res_partner.py (inherited Odoo model)

Concerning *security* and access rights and rules two main files should be used.
First one is the definition of access rights done in a ``ir.model.access.csv``
file. User groups are defined in ``<module>_groups.xml``. Access rules are
defined in ``<model>_security.xml``.

.. code-block:: text

    addons/plant_nursery/
    |-- security/
    |   |-- ir.model.access.csv
    |   |-- plant_nusery_groups.xml
    |   |-- plant_nusery_security.xml
    |   |-- plant_order_security.xml

Concerning *views*, backend views should be split like models and suffixed
by ``_views.xml``. Backend views are list, form, kanban, activity, graph, pivot, ..
views. To ease split by model in views main menus not linked to specific actions
may be extracted into an optional ``<module>_menus.xml`` file. Templates (QWeb
pages used notably for portal / website display) and bundles (import of JS and
CSS assets) are put in separate files. Those are respectively
``<model>_templates.xml`` and ``assets.xml`` files.

.. code-block:: text

    addons/plant_nursery/
    |-- views/
    |   | -- assets.xml (import of JS / CSS)
    |   | -- plant_nursery_menus.xml (optional definition of main menus)
    |   | -- plant_nursery_views.xml (backend views)
    |   | -- plant_nursery_templates.xml (portal templates)
    |   | -- plant_order_views.xml
    |   | -- plant_order_templates.xml
    |   | -- res_partner_views.xml

Concerning *data*, split them by purpose (demo or data) and main model. Filenames
will be the main_model name suffixed by ``_demo.xml`` or ``_data.xml``. For instance
for an application having demo and data for its main model as well as subtypes,
activities and mail templates all related to mail module:

.. code-block:: text

    addons/plant_nursery/
    |-- data/
    |   |-- plant_nursery_data.xml
    |   |-- plant_nursery_demo.xml
    |   |-- mail_data.xml

Concerning *controllers*, generally all controllers belong to a single controller
contained in a file named ``<module_name>.py``. An old convention in Odoo is to
name this file ``main.py`` but it is considered as outdated. If you need to inherit
an existing controller from another module do it in ``<inherited_module_name>.py``.
For example adding portal controller in an application is done in ``portal.py``.

.. code-block:: text

    addons/plant_nursery/
    |-- controllers/
    |   |-- plant_nursery.py
    |   |-- portal.py (inheriting portal/controllers/portal.py)
    |   |-- main.py (deprecated, replaced by plant_nursery.py)

Concerning *static files*, Javascript files follow globally the same logic as
python models. Each component should be in its own file with a meaningful name.
For instance, the activity widgets are located in ``activity.js`` of mail module.
Subdirectories can also be created to structure the 'package' (see web module
for more details). The same logic should be applied for the templates of JS
widgets (static XML files) and for their styles (scss files). Don't link
data (image, libraries) outside Odoo: do not use an URL to an image but copy
it in the codebase instead.

Concerning *wizards*, naming convention is the same of for python models:
``<transient>.py`` and ``<transient>_views.xml``. Both are put in the wizard
directory. This naming comes from old odoo applications using the wizard
keyword for transient models.

.. code-block:: text

    addons/plant_nursery/
    |-- wizard/
    |   |-- make_plant_order.py
    |   |-- make_plant_order_views.xml

Concerning *statistics reports* done with python / SQL views and classic views
naming is the following :

.. code-block:: text

    addons/plant_nursery/
    |-- report/
    |   |-- plant_order_report.py
    |   |-- plant_order_report_views.xml

Concerning *printable reports* which contain mainly data preparation and Qweb
templates naming is the following :

.. code-block:: text

    addons/plant_nursery/
    |-- report/
    |   |-- plant_order_reports.xml (report actions, paperformat, ...)
    |   |-- plant_order_templates.xml (xml report templates)

The complete tree of our Odoo module therefore looks like

.. code-block:: text

    addons/plant_nursery/
    |-- __init__.py
    |-- __manifest__.py
    |-- controllers/
    |   |-- __init__.py
    |   |-- plant_nursery.py
    |   |-- portal.py
    |-- data/
    |   |-- plant_nursery_data.xml
    |   |-- plant_nursery_demo.xml
    |   |-- mail_data.xml
    |-- models/
    |   |-- __init__.py
    |   |-- plant_nursery.py
    |   |-- plant_order.py
    |   |-- res_partner.py
    |-- report/
    |   |-- __init__.py
    |   |-- plant_order_report.py
    |   |-- plant_order_report_views.xml
    |   |-- plant_order_reports.xml (report actions, paperformat, ...)
    |   |-- plant_order_templates.xml (xml report templates)
    |-- security/
    |   |-- ir.model.access.csv
    |   |-- plant_nusery_groups.xml
    |   |-- plant_nusery_security.xml
    |   |-- plant_order_security.xml
    |-- static/
    |   |-- img/
    |   |   |-- my_little_kitten.png
    |   |   |-- troll.jpg
    |   |-- lib/
    |   |   |-- external_lib/
    |   |-- src/
    |   |   |-- js/
    |   |   |   |-- widget_a.js
    |   |   |   |-- widget_b.js
    |   |   |-- scss/
    |   |   |   |-- widget_a.scss
    |   |   |   |-- widget_b.scss
    |   |   |-- xml/
    |   |   |   |-- widget_a.xml
    |   |   |   |-- widget_a.xml
    |-- views/
    |   |-- assets.xml
    |   |-- plant_nursery_menus.xml
    |   |-- plant_nursery_views.xml
    |   |-- plant_nursery_templates.xml
    |   |-- plant_order_views.xml
    |   |-- plant_order_templates.xml
    |   |-- res_partner_views.xml
    |-- wizard/
    |   |--make_plant_order.py
    |   |--make_plant_order_views.xml

.. note:: File names should only contain ``[a-z0-9_]`` (lowercase
          alphanumerics and ``_``)

.. warning:: Use correct file permissions : folder 755 and file 644.

XML files
=========

Format
------
To declare a record in XML, the **record** notation (using *<record>*) is recommended:

- Place ``id`` attribute before ``model``
- For field declaration, ``name`` attribute is first. Then place the
  *value* either in the ``field`` tag, either in the ``eval``
  attribute, and finally other attributes (widget, options, ...)
  ordered by importance.

- Try to group the record by model. In case of dependencies between
  action/menu/views, this convention may not be applicable.
- Use naming convention defined at the next point
- The tag *<data>* is only used to set not-updatable data with ``noupdate=1``.
  If there is only not-updatable data in the file, the ``noupdate=1`` can be
  set on the ``<odoo>`` tag and do not set a ``<data>`` tag.

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

Odoo supports :ref:`custom tags <reference/data/shortcuts>` acting as syntactic sugar:

- menuitem: use it as a shortcut to declare a ``ir.ui.menu``
- template: use it to declare a QWeb View requiring only the ``arch`` section of the view.
- report: use to declare a :ref:`report action <reference/actions/report>`
- act_window: use to declare a :ref:`window action <reference/actions/window>`

The 4 first tags are prefered over the :ref:`record <reference/data/record>` notation.


XML IDs and naming
------------------

Security, View and Action
~~~~~~~~~~~~~~~~~~~~~~~~~

Use the following pattern :

* For a menu: :samp:`{<model_name>}_menu`, or :samp:`{<model_name>}_menu_{do_stuff}` for submenus.
* For a view: :samp:`{<model_name>}_view_{<view_type>}`, where *view_type* is
  ``kanban``, ``form``, ``tree``, ``search``, ...
* For an action: the main action respects :samp:`{<model_name>}_action`.
  Others are suffixed with :samp:`_{<detail>}`, where *detail* is a
  lowercase string briefly explaining the action. This is used only if
  multiple actions are declared for the model.
* For window actions: suffix the action name by the specific view information
  like :samp:`{<model_name>}_action_view_{<view_type}`.
* For a group: :samp:`{<model_name>}_group_{<group_name>}` where *group_name*
  is the name of the group, generally 'user', 'manager', ...
* For a rule: :samp:`{<model_name>}_rule_{<concerned_group>}` where
  *concerned_group* is the short name of the concerned group ('user'
  for the 'model_name_group_user', 'public' for public user, 'company'
  for multi-company rules, ...).

Name should be identical to xml id with dots replacing underscores. Actions
should have a real naming as it is used as display name.

.. code-block:: xml

    <!-- views  -->
    <record id="model_name_view_form" model="ir.ui.view">
        <field name="name">model.name.view.form</field>
        ...
    </record>

    <record id="model_name_view_kanban" model="ir.ui.view">
        <field name="name">model.name.view.kanban</field>
        ...
    </record>

    <!-- actions -->
    <record id="model_name_action" model="ir.act.window">
        <field name="name">Model Main Action</field>
        ...
    </record>

    <record id="model_name_action_child_list" model="ir.actions.act_window">
        <field name="name">Model Access Childs</field>
    </record>

    <!-- menus and sub-menus -->
    <menuitem
        id="model_name_menu_root"
        name="Main Menu"
        sequence="5"
    />
    <menuitem
        id="model_name_menu_action"
        name="Sub Menu 1"
        parent="module_name.module_name_menu_root"
        action="model_name_action"
        sequence="10"
    />

    <!-- actions -->
    <act_window id="model_name_action">
        ...
    </act_window>

    <act_window id="model_name_action_child_list">
        ...
    </act_window>

    <!-- security -->
    <record id="module_name_group_user" model="res.groups">
        ...
    </record>

    <record id="model_name_rule_public" model="ir.rule">
        ...
    </record>

    <record id="model_name_rule_company" model="ir.rule">
        ...
    </record>

Inheriting XML
~~~~~~~~~~~~~~

Xml Ids of inheriting views should use the same ID as the original record.
It helps finding all inheritance at a glance. As final Xml Ids are prefixed
by the module that creates them there is no overlap.

.. note:: View names use dot notation ``my.model.view_type`` or
          ``my.model.view_type.inherit`` instead of *"This is the form view of
          My Model"*.

Naming should contain an ``.inherit.{details}`` suffix to ease understanding
the override purpose when looking at its name.

.. code-block:: xml

    <record id="model_view_form" model="ir.ui.view">
        <field name="name">model.view.form.inherit.module2</field>
        <field name="inherit_id" ref="module1.model_view_form"/>
        ...
    </record>

New primary views do not require the inherit suffix as those are new records
based upon the first one.

.. code-block:: xml

    <record id="module2.model_view_form" model="ir.ui.view">
        <field name="name">model.view.form.module2</field>
        <field name="inherit_id" ref="module1.model_view_form"/>
        <field name="mode">primary</field>
        ...
    </record>

Python
======

PEP8 options
------------

Using a linter can help show syntax and semantic warnings or errors.
We recommend `flake8 <https://pypi.python.org/pypi/flake8>`_ for Python and
`jshint <http://jshint.com/install/>`_ for JavaScript.
Odoo source code tries to respect Python standard, but some of them can be ignored.


- E501: line too long

.. note:: A good max line length standard would be **99** characters for us,
          but not mandatory.

- E301: expected 1 blank line, found 0
- E302: expected 2 blank lines, found 1

Imports
-------
The imports are ordered as

#. External libraries (one per line sorted and split in python stdlib)
#. Imports of ``odoo``
#. Imports from Odoo modules (rarely, and only if necessary)

Inside these 3 groups, the imported lines are alphabetically sorted.

.. code-block:: python

    # 1 : imports of python lib
    import base64
    import re
    import time
    from datetime import datetime
    # 2 :  imports of odoo
    import odoo
    from odoo import api, fields, models # alphabetically ordered
    from odoo.tools.safe_eval import safe_eval as eval
    from odoo.tools.translate import _
    # 3 :  imports from odoo addons
    from odoo.addons.website.models.website import slug
    from odoo.addons.web.controllers.main import login_redirect


Idiomatics of Programming (Python)
----------------------------------

- Always favor *readability* over *conciseness* or using the language features or idioms.

- Think about *performance* and :ref:`*security* <reference/security/guidelines>` all along the development process.

- As a good developper, document your code (docstrings on methods, simple
  comments for tricky part of code)

- As python is the main language of Odoo models, know it =) :

  - Know your builtins : You should at least have a basic understanding of all
    the Python builtins (http://docs.python.org/library/functions.html)

  - Learn list/dict comprehensions : Use list comprehension, dict comprehension, and
    basic manipulation using ``map``, ``filter``, ``sum``, ... They make the code
    easier to read.

  - Don't hesitate to refresh your knowledge (http://learnxinyminutes.com/docs/python/) or
    to get more familiar with Python (https://docs.python.org/3/tutorial/)


Programming in Odoo
-------------------

- Avoid to create generators and decorators: only use the ones provided by
  the Odoo API.
- As in python, use ``filtered``, ``mapped``, ``sorted``, ... :ref:`ORM <reference/orm>` methods to
  ease code reading and performance.
- Don't reinvent the wheel : Use or extend existing functionalities when you need them.
    Use :ref:` Odoo Mixins <reference/mixins/` to integrate interesting functionalities easily.

Make your method work in batch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
When adding a function, make sure it can process multiple records (:ref:`recordsets <reference/orm>`). Typically,
such methods are decorated with the ``api.multi`` decorator. Then you will have
to iterate on ``self`` to treat each record.

.. code-block:: python

    @api.multi
    def my_method(self)
        for record in self:
            record.do_cool_stuff()

.. note :: Avoid to use ``api.one``  decorator : this will probably not do what you expected,
              and extending a such method is not as easy than a *api.multi* method, since it
              returns a list of result (ordered by recordset ids).

For performance issue, when developping a 'stat button' (for instance), do not
perform a ``search`` or a ``search_count`` in a loop in a ``api.multi`` method. It
is recommended to use ``read_group`` method, to compute all value in only one request.

.. code-block:: python

    @api.multi
    def _compute_equipment_count(self):
    """ Count the number of equipement per category """
        equipment_data = self.env['hr.equipment'].read_group([('category_id', 'in', self.ids)], ['category_id'], ['category_id'])
        mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in equipment_data])
        for category in self:
            category.equipment_count = mapped_data.get(category.id, 0)


Propagate the context
~~~~~~~~~~~~~~~~~~~~~
The context is a ``frozendict`` that cannot be modified. To call a method with
a different context, the ``with_context`` method should be used :

.. code-block:: python

    records.with_context(new_context).do_stuff() # all the context is replaced
    records.with_context(**additionnal_context).do_other_stuff() # additionnal_context values override native context ones

.. note :: Passing parameter in context can have dangerous side-effects. Since the values
      are propagated automatically, some behavior can appears. Calling ``create()``
      method of a model with *default_my_field* key in context will set the default
      value of *my_field* for the concerned model. But if curing this creation, other
      object (such as sale.order.line, on sale.order creation) having a field
      name *my_field*, their default value will be set too.

If you need to create a key context influencing the behavior of some object,
choose a good name, and eventually prefix it by the name of the module to
isolate its impact. A good example are the keys of ``mail`` module :
*mail_create_nosubscribe*, *mail_notrack*, *mail_notify_user_signature*, ...



Think extendable
~~~~~~~~~~~~~~~~
Functions and methods should not contain too much logic: having a lot of small
and simple methods is more advisable than having few large and complex methods.
A good rule of thumb is to split a method as soon as it has more than one
responsibility (see http://en.wikipedia.org/wiki/Single_responsibility_principle).

Hardcoding a business logic in a method should be avoided as it prevents
an easy extension by a submodule.

.. code-block:: python

    # do not do this
    # modifying the domain or criteria implies overriding whole method
    def action(self):
        ...  # long method
        partners = self.env['res.partner'].search(complex_domain)
        emails = partners.filtered(lambda r: arbitrary_criteria).mapped('email')

    # better but do not do this either
    # modifying the logic forces to duplicate some parts of the code
    def action(self):
        ...
        partners = self._get_partners()
        emails = partners._get_emails()

    # better
    # minimum override
    def action(self):
        ...
        partners = self.env['res.partner'].search(self._get_partner_domain())
        emails = partners.filtered(lambda r: r._filter_partners()).mapped('email')

The above code is over extendable for the sake of example but the readability
must be taken into account and a tradeoff must be made.

Also, name your functions accordingly: small and properly named functions are
the starting point of readable/maintainable code and tighter documentation.

This recommendation is also relevant for classes, files, modules and packages.
(See also http://en.wikipedia.org/wiki/Cyclomatic_complexity)

Use translation method correctly
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Odoo uses a GetText-like method named "underscore" ``_( )`` to indicate that
a static string used in the code needs to be translated at runtime using the
language of the context. This pseudo-method is accessed within your code by
importing as follows:

.. code-block:: python

    from odoo.tools.translate import _

A few very important rules must be followed when using it, in order for it to
work and to avoid filling the translations with useless junk.

Basically, this method should only be used for static strings written manually
in the code, it will not work to translate field values, such as Product names,
etc. This must be done instead using the translate flag on the corresponding
field.

The rule is very simple: calls to the underscore method should always be in
the form ``_('literal string')`` and nothing else:

.. code-block:: python

    # good: plain strings
    error = _('This record is locked!')

    # good: strings with formatting patterns included
    error = _('Record %s cannot be modified!') % record

    # ok too: multi-line literal strings
    error = _("""This is a bad multiline example
                 about record %s!""") % record
    error = _('Record %s cannot be modified' \
              'after being validated!') % record

    # bad: tries to translate after string formatting
    #      (pay attention to brackets!)
    # This does NOT work and messes up the translations!
    error = _('Record %s cannot be modified!' % record)

    # bad: dynamic string, string concatenation, etc are forbidden!
    # This does NOT work and messes up the translations!
    error = _("'" + que_rec['question'] + "' \n")

    # bad: field values are automatically translated by the framework
    # This is useless and will not work the way you think:
    error = _("Product %s is out of stock!") % _(product.name)
    # and the following will of course not work as already explained:
    error = _("Product %s is out of stock!" % product.name)

    # bad: field values are automatically translated by the framework
    # This is useless and will not work the way you think:
    error = _("Product %s is not available!") % _(product.name)
    # and the following will of course not work as already explained:
    error = _("Product %s is not available!" % product.name)

    # Instead you can do the following and everything will be translated,
    # including the product name if its field definition has the
    # translate flag properly set:
    error = _("Product %s is not available!") % product.name


Also, keep in mind that translators will have to work with the literal values
that are passed to the underscore function, so please try to make them easy to
understand and keep spurious characters and formatting to a minimum. Translators
must be aware that formatting patterns such as %s or %d, newlines, etc. need
to be preserved, but it's important to use these in a sensible and obvious manner:

.. code-block:: python

    # Bad: makes the translations hard to work with
    error = "'" + question + _("' \nPlease enter an integer value ")

    # Better (pay attention to position of the brackets too!)
    error = _("Answer to question %s is not valid.\n" \
              "Please enter an integer value.") % question

In general in Odoo, when manipulating strings, prefer ``%`` over ``.format()``
(when only one variable to replace in a string), and prefer ``%(varname)`` instead
of position (when multiple variables have to be replaced). This makes the
translation easier for the community translators.


Symbols and Conventions
-----------------------

- Model name (using the dot notation, prefix by the module name) :
    - When defining an Odoo Model : use singular form of the name (*res.partner*
      and *sale.order* instead of *res.partnerS* and *saleS.orderS*)
    - When defining an Odoo Transient (wizard) : use ``<related_base_model>.<action>``
      where *related_base_model* is the base model (defined in *models/*) related
      to the transient, and *action* is the short name of what the transient do. Avoid the *wizard* word.
      For instance : ``account.invoice.make``, ``project.task.delegate.batch``, ...
    - When defining *report* model (SQL views e.i.) : use
      ``<related_base_model>.report.<action>``, based on the Transient convention.

- Odoo Python Class : use camelcase (Object-oriented style).


.. code-block:: python

    class AccountInvoice(models.Model):
        ...

- Variable name :
    - use camelcase for model variable
    - use underscore lowercase notation for common variable.
    - suffix your variable name with *_id* or *_ids* if it contains a record id or list of id. Don't use ``partner_id`` to contain a record of res.partner

.. code-block:: python

    Partner = self.env['res.partner']
    partners = Partner.browse(ids)
    partner_id = partners[0].id

- ``One2Many`` and ``Many2Many`` fields should always have *_ids* as suffix (example: sale_order_line_ids)
- ``Many2One`` fields should have *_id* as suffix (example : partner_id, user_id, ...)
- Method conventions
    - Compute Field : the compute method pattern is *_compute_<field_name>*
    - Search method : the search method pattern is *_search_<field_name>*
    - Default method : the default method pattern is *_default_<field_name>*
    - Selection method: the selection method pattern is *_selection_<field_name>*
    - Onchange method : the onchange method pattern is *_onchange_<field_name>*
    - Constraint method : the constraint method pattern is *_check_<constraint_name>*
    - Action method : an object action method is prefix with *action_*. Its decorator is
      ``@api.multi``, but since it use only one record, add ``self.ensure_one()``
      at the beginning of the method.

- In a Model attribute order should be
    #. Private attributes (``_name``, ``_description``, ``_inherit``, ...)
    #. Default method and ``_default_get``
    #. Field declarations
    #. Compute, inverse and search methods in the same order as field declaration
    #. Selection method (methods used to return computed values for selection fields)
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
        event_type = fields.Selection(string="Type", selection='_selection_type')

        # compute and search fields, in the same order of fields declaration
        @api.multi
        @api.depends('seats_max', 'registration_ids.state', 'registration_ids.nb_register')
        def _compute_seats(self):
            ...

        @api.model
        def _selection_type(self):
            return []

        # Constraints and onchanges
        @api.constrains('seats_max', 'seats_available')
        def _check_seats_limit(self):
            ...

        @api.onchange('date_begin')
        def _onchange_date_begin(self):
            ...

        # CRUD methods (and name_get, name_search, ...) overrides
        def create(self, values):
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

Static files organization
--------------------------

Odoo addons have some conventions on how to structure various files. We explain
here in more details how web assets are supposed to be organized.

The first thing to know is that the Odoo server will serve (statically) all files
located in a *static/* folder, but prefixed with the addon name. So, for example,
if a file is located in *addons/web/static/src/js/some_file.js*, then it will be
statically available at the url *your-odoo-server.com/web/static/src/js/some_file.js*

The convention is to organize the code according to the following structure:

- *static*: all static files in general
- *static/lib*: this is the place where js libs should be located, in a sub folder.
  So, for example, all files from the *jquery* library are in *addons/web/static/lib/jquery*
- *static/src*: the generic static source code folder
- *static/src/css*: all css files
- *static/src/fonts*
- *static/src/img*
- *static/src/js*
- *static/src/scss*: scss files
- *static/src/xml*: all qweb templates that will be rendered in JS
- *static/tests*: this is where we put all test related files.

Javascript coding guidelines
----------------------------

- ``use strict;`` is recommended for all javascript files
- Use a linter (jshint, ...)
- Never add minified Javascript Libraries
- Use camelcase for class declaration

More precise JS guidelines are detailed at https://github.com/odoo/odoo/wiki/Javascript-coding-guidelines.
You may also have a look at existing API in Javascript by looking Javascript
References.

CSS coding guidelines
---------------------

- Prefix all your classes with *o_<module_name>* where *module_name* is the
  technical name of the module ('sale', 'im_chat', ...) or the main route
  reserved by the module (for website module mainly, i.e. : 'o_forum' for
  *website_forum* module). The only exception for this rule is the
  webclient: it simply uses *o_* prefix.
- Avoid using *id* tag
- Use Bootstrap native classes
- Use underscore lowercase notation to name class

Git
===

Configure your git
------------------

Based on ancestral experience and oral tradition, the following things go a long
way towards making your commits more helpful:

- Be sure to define both the user.email and user.name in your local git config

  .. code-block:: text

     git config --global <var> <value>

- Be sure to add your full name to your Github profile here. Please feel fancy
  and add your team, avatar, your favorite quote, and whatnot ;-)

Commit message structure
------------------------

Commit message has four parts: tag, module, short description and full
description. Try to follow the preferred structure for your commit messages

.. code-block:: text

  [TAG] module: describe your change in a short sentence (ideally < 50 chars)

  Long version of the change description, including the rationale for the change,
  or a summary of the feature being introduced.

  Please spend a lot more time describing WHY the change is being done rather
  than WHAT is being changed. This is usually easy to grasp by actually reading
  the diff. WHAT should be explained only if there are technical choices
  or decision involved. In that case explain WHY this decision was taken.

  End the message with references, such as task or bug numbers, PR numbers, and
  OPW tickets, following the suggested format:
  Related to task #taskId
  Fixes #12345  (link and close issue on Github)
  Closes #7865  (link and close PR on Github)
  OPW-112233

Tag and module name
-------------------

Tags are used to prefix your commit. They should be one of the following

- **[FIX]** for bug fixes: mostly used in stable version but also valid if you
  are fixing a recent bug in development version;
- **[REF]** for refactoring: when a feature is heavily rewritten;
- **[ADD]** for adding new modules;
- **[REM]** for removing resources: removing dead code, removing views,
  removing modules, ...;
- **[REV]** for reverting commits: if a commit causes issues or is not wanted
  reverting it is done using this tag;
- **[MOV]** for moving files: use git move and do not change content of moved file
  otherwise Git may loose track and history of the file; also used when moving
  code from one file to another;
- **[REL]** for release commits: new major or minor stable versions;
- **[IMP]** for improvements: most of the changes done in development version
  are incremental improvements not related to another tag;
- **[MERGE]** for merge commits: used in forward port of bug fixes but also as
  main commit for feature involving several separated commits;
- **[CLA]** for signing the Odoo Individual Contributor License;
- **[I18N]** for changes in translation files;

After tag comes the modified module name. Use the technical name as functional
name may change with time. If several modules are modified, list them or use
various to tell it is cross-modules. Unless really required or easier avoid
modifying code across several modules in the same commit. Understanding module
history may become difficult.

Commit message header
---------------------

After tag and module name comes a meaningful commit message header. It should be
self explanatory and include the reason behind the change. Do not use single words
like "bugfix" or "improvements". Try to limit the header length to about 50 characters
for readability.

Commit message header should make a valid sentence once concatenated with
``if applied, this commit will <header>``. For example ``[IMP] base: prevent to
archive users linked to active partners`` is correct as it makes a valid sentence
``if applied, this commit will prevent users to archive...``.

Commit message full description
-------------------------------

In the message description specify the part of the code impacted by your changes
(module name, lib, transversal object, ...) and a description of the changes.

First explain WHY you are modifying code. What is important if someone goes back
to your commit in about 4 decades (or 3 days) is why you did it. It is the
purpose of the change.

What you did can be found in the commit itself. If there was some technical choices
involved it is a good idea to explain it also in the commit message after the why.
For Odoo R&D developers "PO team asked me to do it" is not a valid why, by the way.

Please avoid commits which simultaneously impact multiple modules. Try to split
into different commits where impacted modules are different. It will be helpful
if we need to revert changes in a given module separately.

Don't hesitate to be a bit verbose. Most people will only see your commit message
and judge everything you did in your life just based on those few sentences.
No pressure at all.

**You spend several hours, days or weeks working on meaningful features. Take
some time to calm down and write clear and understandable commit messages.**

If you are an Odoo R&D developer the WHY should be the purpose of the task you
are working on. Full specifications make the core of the commit message.
**If you are working on a task that lacks purpose and specifications please
consider making them clear before continuing.**

Finally here are some examples of correct commit messages :

.. code-block:: text

 [REF] models: use `parent_path` to implement parent_store

  This replaces the former modified preorder tree traversal (MPTT) with the
  fields `parent_left`/`parent_right`[...]

 [FIX] account: remove frenglish

  [...]

  Closes #22793
  Fixes #22769

 [FIX] website: remove unused alert div, fixes look of input-group-btn

  Bootstrap's CSS depends on the input-group-btn
  element being the first/last child of its parent.
  This was not the case because of the invisible
  and useless alert.

.. note:: Use the long description to explain the *why* not the
          *what*, the *what* can be seen in the diff
