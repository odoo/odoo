=======
Backend
=======

Build an Odoo module
====================

Odoo uses a client/server architecture in which clients are web browsers
accessing the odoo server via RPC.

Business logic and extension is generally performed on the server side,
although supporting client features (e.g. new data representation such as
interactive maps) can be added to the client.

Both server and client extensions are packaged as *modules* which are
optionally loaded in a *database*.

Odoo modules can either add brand new business logic to an Odoo system, or
alter and extend existing business logic: a module can be created to add your
country's accounting rules to Odoo's generic accounting support, while the
next module adds support for real-time visualisation of a bus fleet.

Everything in Odoo thus starts and ends with modules.

Composition of a module
-----------------------

.. todo:: graph? Physical / logical composition?

An Odoo module can contain a number of elements:

Business objects
    declared as Python classes, these resources are automatically persisted
    by Odoo based on their configuration

Data files
    XML or CSV files declaring metadata (views or workflows), configuration
    data (modules parameterization), demonstration data and more

Web controllers
    Handle requests from web browsers

Static web data
    Images, CSS or javascript files used by the web interface or website

Module structure
----------------

.. todo:: redundant with same section in web howto, use include? separate
          intro to modules structure?

Each module is a directory within a *module directory*. Module directories
are specified by using the :option:`--addons-path <odoo.py --addons-path>`
option.

.. tip:: most command-line options can also be set using a configuration file
    :class: aphorism

    .. todo:: reference for config file?

An Odoo module is declared by its :ref:`manifest <core/module/manifest>`. It
is mandatory and contains a single python dictionary declaring various
metadata for the module: the module's name and description, list of Odoo
modules required for this one to work properly, references to data files, …

Its general structure is the following::

    {
        'name': "MyModule",
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

A module is also a
`Python package <http://docs.python.org/2/tutorial/modules.html#packages>`_
with a ``__init__.py`` file, containing import instructions for various Python
files in the module.

For instance, if the module has a single ``mymodule.py`` file ``__init__.py``
might contain::

    import mymodule

.. admonition:: Exercise 1 — module creation
    :class: exercise

    Create an empty module Open Academy, install it in Odoo

    .. only:: solutions

        #. Create a new folder ``openacademy``
        #. Create an empty ``openacademy/__init__.py`` file
        #. Create an ``openacademy/__openerp__.py`` file with:

           .. literalinclude:: backend/exercise1/__openerp__.py

Object-Relational Mapping
-------------------------

A key component of Odoo is the :abbr:`ORM (Object-Relational Mapping)` layer.
This layer avoids having to write :abbr:`SQL (Structured Query Language)` by
hand and provide extensibility and security services.

Business objects are declared as Python classes extending
:class:`~openerp.models.Model` which integrates them into the automated
persistence system.

Models can be configured by setting a number of attributes at their
definition, the most important being ``_name`` which is *required* and defines
the name for the model in the Odoo system. Here is a minimally complete
definition of a model::

    from openerp import models
    class MinimalModel(models.Model):
        _name = 'test.model'

Model fields
------------

Fields are used to define the model's data storage capabilities. Fields are
defined as attributes on the model class::

    from openerp import models, fields

    class LessMinimalModel(models.Model):
        _name = 'test.model2'

        name = fields.Char()

Common Attributes
#################

Field attributes are passed as parameters to the field, e.g.

::

    name = field.Char(readonly=True)

Some attributes are available on all fields, here are the most common ones:

:attr:`~openerp.fields.Field.string` (``unicode``, defaults to field's name)
    The label of the field in UI (visible by users).
:attr:`~openerp.fields.Field.required` (``bool``, defaults to ``False``)
    If ``True``, the field can not be empty, it must either have a default
    value or always be given a value when creating a record.
:attr:`~openerp.fields.Field.help` (``unicode``, defaults to empty)
    Long-formm, provides a help tooltip to users in the UI.
:attr:`~openerp.fields.Field.select` (``bool``, defaults to ``False``)
    Requests that Odoo create a `database index`_ on the column

Simple fields
#############

There are two broad categories of fields: "simple" fields which are atomic
values stored directly in the model's table and "relational" fields linking
records (of the same model or of different models).

Example of simple fields are :class:`~openerp.fields.Boolean`,
:class:`~openerp.fields.Date`, :class:`~openerp.fields.Char`.

Reserved fields
###############

Odoo creates a few fields in all models\ [#autofields]_. These fields are
managed by the system and shouldn't be written to (they can be read):

``id`` (:class:`~openerp.fields.Id`)
    the unique identifier for a record in its model
``create_date`` (:class:`~openerp.fields.Datetime`)
    creation date of the record
``create_uid`` (:class:`~openerp.fields.Many2one`)
    user who created the record
``write_date`` (:class:`~openerp.fields.Datetime`)
    last modification date of the record
``write_uid`` (:class:`~openerp.fields.Many2one`)
    user who last modified the record

Special fields
##############

By default, Odoo also requires a ``name`` field on all models for various
display and search behaviors. The field use thus can be overridden using
:attr:`~openerp.models.Model._rec_name`.

.. admonition:: Exercise 2 — define a model
    :class: exercise

    Define a new data model *Course* in the *openacademy* module. A course
    has a name, or "title", and a description. All courses must have a name.


    .. only:: solutions

        #. Create a new file ``openacademy/course.py`` with the content:

           .. literalinclude:: backend/exercise2/course.py

        #. To the existing ``openacademy/__init__.py`` add:

           .. literalinclude:: backend/exercise2/__init__.py

Actions and Menus
-----------------

Actions are declared as regular records and can be triggered in three ways:

#. by clicking on menu items (linked to specific actions)
#. by clicking on buttons in views (if these are connected to actions)
#. as contextual actions on object

.. todo:: maybe <record> should be introduced before shortcuts?

Menus are also regular records in the ORM, there is a ``<menuitem>`` shortcut
to declare an ``ir.ui.menu`` and connect it to the corresponding action more
easily.

The following example defines a menu item to display the list of ideas. The
action associated to the menu mentions the model of the records to display,
and which views are enabled; in this example, only the tree and form views
will be available. There are other optional fields for actions, see the
documentation for a complete description of them.

.. code-block:: xml

    <record model="ir.actions.act_window" id="action_list_ideas">
      <field name="name">Ideas</field>
      <field name="res_model">idea.idea</field>
      <field name="view_mode">tree,form</field>
      <field name="help" type="html">
        <p class="oe_view_nocontent_create">
          A nice arrow with some help for your first record</p>
        </field>
      </record>
      <menuitem id="menu_ideas" parent="menu_root" name="Ideas" sequence="10"
                action="action_list_ideas"/>

.. danger::
    :class: aphorism

    The action must be declared before its corresponding menu in the XML file.

    Data files are executed sequentially, the action's ``id`` must be present
    in the database before the menu can be created.

.. admonition:: Exercise 3 — Define new menu entries
    :class: exercise

    Define new menu entries to access courses and sessions under the
    OpenAcademy menu entry. A user should be able to

    #) display a list of all the courses
    #) create/modify courses

    .. only:: solutions

        #. Create ``openacademy/views/openacademy.xml``:

           .. literalinclude:: backend/exercise3/openacademy.xml
                :language: xml

        #. In ``openacademy/__openerp__.py`` add to the ``data`` list:

           .. literalinclude:: backend/exercise3/__openerp__.py
               :lines: 13-15

Building views: basics
======================

Views form a hierarchy. Several views of the same type can be declared on the
same object, and will be used depending on their priorities.

It is also possible to add/remove elements in a view by declaring an inherited
view (see :ref:`view inheritance <core/views/inheritance>`).

Generic view declaration
------------------------

A view is declared as a record of the model ``ir.ui.view``. Such a record is
declared in XML as

.. code-block:: xml

    <record model="ir.ui.view" id="view_id">
      <field name="name">view.name</field>
      <field name="model">object_name</field>
      <field name="priority" eval="16"/>
      <field name="arch" type="xml">
        <!-- view content: <form>, <tree>, <graph>, ... -->
      </field>
    </record>

.. danger:: The view's content is XML.
    :class: aphorism

    The ``arch`` field must thus be declared as ``type="xml"`` to be parsed
    correctly.

Tree views
----------

Tree views, also called list views, display records in a tabular form. They
are defined with the XML element ``<tree>``. In its simplest form, it mentions
the fields that must be used as the columns of the table.

.. code-block:: xml

    <tree string="Idea list">
      <field name="name"/>
      <field name="inventor_id"/>
    </tree>

Form views
----------

Forms allow the creation/edition of resources, and are defined by XML elements
``<form>``. The following ex- ample shows how a form view can be spatially
structured with separators, groups, notebooks, etc. Consult the documentation
to find out all the possible elements you can place on a form.

.. code-block:: xml

    <form string="Idea form">
      <group colspan="2" col="2">
        <separator string="General stuff" colspan="2"/>
        <field name="name"/>
        <field name="inventor_id"/>
      </group>

      <group colspan="2" col="2">
        <separator string="Dates" colspan="2"/>
        <field name="active"/>
        <field name="invent_date" readonly="1"/>
      </group>

      <notebook colspan="4">
        <page string="Description">
          <field name="description" nolabel="1"/>
        </page>
      </notebook>

      <field name="state"/>
    </form>

.. todo:: isn't version 7 the default now?

.. todo:: might be smart to have the same view in both versions...

Now with the new version 7 you can write html in your form

.. code-block:: xml

    <form string="Idea Form v7" version="7.0">
      <header>
        <button string="Confirm" type="object" name="action_confirm"
                states="draft" class="oe_highlight" />
        <button string="Mark as done" type="object" name="action_done"
                states="confirmed" class="oe_highlight"/>
        <button string="Reset to draft" type="object" name="action_draft"
                states="confirmed,done" />
        <field name="state" widget="statusbar"/>
      </header>
      <sheet>
        <div class="oe_title">
          <label for="name" class="oe_edit_only" string="Idea Name" />
          <h1><field name="name" /></h1>
        </div>
        <separator string="General" colspan="2" />
        <group colspan="2" col="2">
          <field name="description" placeholder="Idea description..." />
        </group>
      </sheet>
    </form>

.. admonition:: Exercise 1 - Customise form view using XML
    :class: exercise

    Create your own form view for the Course object. Data displayed should be:
    the name and the description of the course.

    .. only:: solutions

        .. todo:: step 2 with better alignments & stuff e.g. colspan=4 on fields?

        .. literalinclude:: backend/exercise4/openacademy.xml
            :lines: 4-13
            :language: xml

.. admonition:: Exercise 2 - Notebooks
    :class: exercise

    In the Course form view, put the description field under a tab, such that
    it will be easier to add other tabs later, containing additional
    information.

    .. only:: solutions

        Modify the Course form view as follows:

        .. literalinclude:: backend/exercise5/openacademy.xml
            :lines: 4-20
            :language: xml

Relations between objects
=========================

.. admonition:: Exercise 1 — create models
    :class: exercise

    Create models for *sessions* and *attendees*, add an action and a menu
    item to display the sessions.

    A session has a name, a start date, a duration and a number of seats.

    An attendee has a name.

    .. only:: solutions

        Create classes *Session* and *Attendee*:

        .. literalinclude:: backend/exercise6/course.py
            :lines: 10-

        .. note:: ``digits=(6, 2)`` specifies the precision of a float number:
                  6 is the total number of digits, while 2 is the number of
                  digits after the comma. Note that it results in the number
                  digits before the comma is a maximum 4

Relational fields
-----------------

Relational fields link records, either of the same model (hierarchies) or
between different models.

Relationalf field types are:

:class:`~openerp.fields.Many2one(other_model, ondelete='set null')`
    A simple link to an other object

    .. todo:: UI picture

    .. seealso:: `foreign keys <http://www.postgresql.org/docs/9.3/static/tutorial-fk.html>`_

:class:`~openerp.fields.One2many(other_model, related_field)`
    A virtual relationship, inverse of a :class:`~openerp.fields.Many2one`.
    A :class:`~openerp.fields.One2many` behaves as a container of records,
    accessing it results in a (possibly empty) set of records.

    .. todo::

        * UI picture
        * note about necessary m2o (or can it be autogenerated?)

:class:`~openerp.fields.Many2many(other_model)`
    Bidirectional multiple relationship, any record on one side can be related
    to any number of records on the other side

    .. todo::

        * UI picture

.. admonition:: Exercise 2 — Relations many2one
    :class: exercise

    Using a many2one, modify the *Course*, *Session* and *Attendee* models to
    reflect their relation with one another

    <insert schema here>

    .. only:: solutions

        #. Modify the classes as follows::

           .. literalinclude:: backend/exercise7/course.py

        #. add access to the session object in ``openacademy/view/openacademy.xml``:

           .. literalinclude:: backend/exercise7/openacademy.xml
               :lines: 53-62
               :language: xml

        .. note::

            In the ``Attendee`` class, the ``name`` field was removed and
            replaced by the partner field directly. This is what ``_rec_name``
            is used for.

.. admonition:: Exercise 3 — Inverse o2m
    :class: exercise

    Using the inverse relational field o2m, modify the models to reflect their
    inverse relations

    .. only:: solutions

        Modify the classes as follows:

        .. literalinclude:: backend/exercise8/course.py
            :lines: 4-27

.. admonition:: Exercise 4 — Views modification
    :class: exercise

    For the *Course* model,

    * the name and instructor for the course should be displayed in the tree
      view
    * the form view should display the course name and responsible (wat?) at
      the top, followed by the course description in a tab and the course
      sessions in a second tab

    For the *Session* model,

    * the name of the session and the session course should be displayed in
      the tree view
    * the form view should display all the session's fields

    Try to lay out the form views so that they're clear and readable.

    .. only:: solutions

        #. Modify the Courses view:

           .. literalinclude:: backend/exercise9/openacademy.xml
                :lines: 4-49
                :language: xml

        #. Create the session views

           .. todo:: is colspan crap really good/necessary?

           .. literalinclude:: backend/exercise9/openacademy.xml
                :lines: 82-121
                :language: xml

Domains
#######

In Odoo, :ref:`core/orm/domains` are lists of criteria used to select a subset
of a model's records. Each criteria is a triple of a field name, an operator
and a value.

For instance, when used on the *Product* model the following domain selects
all *services* with a unit price over *1000*::

    [('product_type', '=', 'service'), ('unit_price', '>', 1000)]

By default criteria are combined with an implicit AND. The logical operators
``&`` (AND), ``|`` (OR) and ``!`` (NOT) can be used to explicitly combine
criteria. They are used in prefix position (the operator is inserted before
its arguments rather than between). For instance to select products "which are
services *OR* have a unit price which is *NOT* between 1000 and 2000"::

    ['|',
        ('product_type', '=', 'service'),
        '!', '&',
            ('unit_price', '>=', 1000),
            ('unit_price', '<', 2000)]

A ``domain`` parameter can be added to relational fields to limit valid
records for the relation when trying to select records in the client UI.

.. admonition:: Exercise 2 — relational fields
    :class: exercise

    When selecting the instructor for a *Session*, only instructors (partners
    with ``is_instructor`` set to ``True``) should be visible.

    .. only:: solutions

        You can either:

        * Modify the *Session* model to have::

              class Session(models.Model):
                  _name = 'openacademy.session'

                  [...]
                  instructor_id = fields.Many2one('res.parter',
                      string="Instructor", domain=[('instructor', '=', True)])
                  [...]

          .. note::

              A domain declared as a literal list is evaluated server-side and
              can't refer to dynamic values on the right-hand side, a domain
              declared as a string is evaluated client-side and allows
              field names on the right-hand side

        * Or modify the ``instructor_id`` field in the *Session*'s view:

          .. code-block:: xml

              <field name="instructor_id" domain="[('instructor', '=', True)]"/>

.. admonition:: Exercise 3 — relational fields bis
    :class: exercise

    Create new partner categories *Teacher / Level 1* and *Teacher / Level 2*.
    The instructor for a session can be either an instructor or a teacher
    (of any level).

    .. only:: solutions

        #. Modify the *Session* model::

            instructor_id = fields.Many2one('res.partner', string="Instructor",
                domain=['|', ('instructor', '=', True),
                             ('category_id.name', 'ilike', "Teacher")])

        #. Modify ``openacademy/view/partner.xml`` to get access to
           *Partner categories*:

           .. code-block:: xml

                <record model="ir.actions.act_window" id="contact_cat_list_action">
                    <field name="name">Contact tags</field>
                    <field name="res_model">res.partner.category</field>
                    <field name="view_type">form</field>
                    <field name="view_mode">tree,form</field>
                </record>

                <menuitem id="contact_cat_menu" name="Contact tags"
                          parent="configuration_menu"
                          action="contact_cat_list_action" />

Inheritance
===========

Model inheritance
-----------------

.. todo:: inheritance graph things

.. seealso::

    * :attr:`~openerp.models.Model._inherit`
    * :attr:`~openerp.models.Model._inherits`

View inheritance
----------------

Rather than modify existing views in place (by overwriting them), Odoo uses
view inheritance where children "extension" views are applied on top of root
views and can add or remove content from their parent.

An extension view references its parent using the ``inherit_id`` field, and
instead of a single view its ``arch`` field is composed of any number of
``xpath`` elements selecting and altering the content of their parent view:

.. code-block:: xml

    <!-- improved idea categories list -->
    <record id="idea_category_list2" model="ir.ui.view">
      <field name="name">id.category.list2</field>
      <field name="model">ir.ui.view</field>
      <field name="inherit_id" ref="id_category_list"/>
      <field name="arch" type="xml">
        <!-- find field description inside tree, and add the field
             idea_ids after it -->
        <xpath expr="/tree/field[@name='description']" position="after">
          <field name="idea_ids" string="Number of ideas"/>
        </xpath>
      </field>
    </record>

``expr``
    An XPath_ expression selecting a single element in the parent view.
    Raises an error if it matches no element or more than one
``position``
    Operation to apply to the matched element:

    ``inside``
        appends ``xpath``'s body at the end of the matched element
    ``replace``
        replaces the matched element by the ``xpath``'s body
    ``before``
        inserts the ``xpath``'s body as a sibling before the matched element
    ``after``
        inserts the ``xpaths``'s body as a sibling after the matched element
    ``attributes``
        alters the attributes of the matched element using special
        ``attribute`` elements in the ``xpath``'s body

.. admonition:: Exercise 1 — alter existing content
    :class: exercise

    * Using model inheritance, modify the existing *Partner* model to add an
      ``is_instructor`` boolean field, and a list of the sessions for which
      the partner is the instructor
    * Using view inheritance, display these fields in the partner form view

    .. only:: solutions

        #. Create a ``openacademy/partner.py`` file:

           .. literalinclude:: backend/exercise11/partner.py

        #. Create an ``openacademy/views/partner.xml``:

           .. note::

               This is the opportunity to introduce the developer mode to
               inspect the view find its ``xml_id`` and the place to put the
               new field.

           .. literalinclude:: backend/exercise11/partner.xml
                :language: xml

        #. Add the following line to ``openacademy/__init__.py``::

            import partner

        #. Finally add the new data file to ``openacademy/__openerp__.py``:

            .. literalinclude:: backend/exercise11/__openerp__.py

Computed fields
===============

So far fields have been stored directly in and retrieved directly from the
database.

Fields can also be *computed*. In that case, the field's value is not
retrieved from the database but computed on-the-fly by calling a method of the
model object.

To create a computed field, create a field and set its
:attr:`~openerp.fields.Field.compute` to the name of a method. The computation
method should simply set its field on its subject::

    import random
    from openerp import api, models

    class ComputedModel(models.Model):
        _name = 'test.computed'

        name = fields.Char(compute='_compute_name')

        @api.one
        def _compute_name(self):
            self.name = str(random.randint(1, 1e6))

.. admonition:: Exercise 1: computed fields
    :class: exercise

    * Add the percentage of filled seats to the *Session* model
    * Display that field in the tree and form views
    * Display the field as a progress bar

    .. only:: solutions

        #. In ``openacademy/course.py``, modify the *Session* model as follows:

           .. literalinclude:: backend/exercise12/course.py

        #. In ``openacademy/views/openacademy.xml`` modify the *Session* view:

           .. literalinclude:: backend/exercise12/openacademy.xml
               :language: xml
               :lines: 94-100
               :emphasize-lines: 6

           .. literalinclude:: backend/exercise12/openacademy.xml
               :language: xml
               :lines: 117-121
               :emphasize-lines: 4

Onchange
========

.. code-block:: xml

    <!-- content of form view -->
    <field name="amount"/>
    <field name="unit_price"/>
    <field name="price" readonly="1"/>

.. code-block:: python

    # onchange handler
    @api.onchange('amount', 'unit_price')
    def _onchange_price(self):
        # set auto-changing field
        self.price = self.amount * self.unit_price
        # Can optionally return a warning and domains
        return {
            'warning': {
                'title': "Something bad happened",
                'message': "It was very bad indeed",
            }
        }

.. todo:: check that this actually works

For computed fields, valued ``onchange`` behavior is built-in as can be seen
by playing with the *Session* form: change the number of seats and the
``seats_taken`` progressbar is automatically updated.

.. admonition:: Exercise 2 — warning
    :class: exercise

    Add an explicit onchange to warn about invalid values

    .. only:: solutions

        .. code-block:: python

            @api.onchange('seats', 'attendee_ids')
            def onchange_seats_taken(self):
                if self.seats < 0:
                    return {
                        'warning': {
                            'title': "Incorrect field value",
                            'message': "The number of seats should not be negativ",
                    }
                if self.seats < len(self.attendee_ids):
                    return {
                        'warning': {
                            'title': "To many attendees",
                            'message': "Increase seats or remove excess attendees",
                        }
                    }

Model invariants
================

* :attr:`~openerp.models.Model._constraints`
* :attr:`~openerp.models.Model._sql_constraints`

.. admonition:: Exercise 4 - Add Python constraints
    :class: exercise

    Add a constraint that checks that the instructor is not present in the attendees of his/her own session.

    .. only:: solutions

        .. code-block:: python

            def _check_instructor_not_in_attendees(self):
                for session in self:
                    partners = [att.partner_id for att in session.attendee_ids]
                    if session.instructor_id and session.instructor_id in partners:
                        return False
                return True

            _constraints = {
                (_check_instructor_not_in_attendees,
                 "The instructor can not be an attendee",
                 ['instructor_id', 'attendee_ids']),
            }

.. admonition:: Exercise 5 - Add SQL constraints
    :class: exercise

    With the help of `PostgreSQL's documentation`_ , add the following
    constraints:

    #. CHECK that the course description and the course title are not the same
    #. Make the Course's name UNIQUE
    #. Make sure the Attendee table can not contain the same partner for the
       same session multiple times (UNIQUE on pairs)

    .. only:: solutions

        #. In the *Course* model

            .. code-block:: python

                _sql_constraints = [
                    ('name_description_check',
                     'CHECK(name != description)',
                     "The title of the course should not be the description"),

                    ('name_unique',
                     'UNIQUE(name)',
                     "The course title must be unique"),
                ]
        #. In the *Attendee* model

            .. code-block:: python

                _sql_constraints = [
                    ('partner_session_unique',
                     'UNIQUE(partner_id, session_id)',
                     "An attendee can not attend the same session multiple times"),
                ]

.. admonition:: Exercise 6 - Add a duplicate option
    :class: exercise

    Since we added a constraint for the Course name uniqueness, it is not
    possible to use the “duplicate” function anymore (Form > Duplicate).
    Re-implement your own “copy” method which allows to duplicate the Course
    object, changing the original name into “Copy of [original name]”.

    .. only:: solutions

        .. code-block:: python

            class Course(models.Model):
                _name = 'openacademy.course'

                @api.one
                def copy(self, default=None):
                    default = dict(default or {})

                    others_count = self.search_count(
                        [('name', '=like', self.name + '%')])
                    if not others_count:
                        new_name = "{} (copy)".format(self.name)
                    else:
                        new_name = "{} (copy {})".format(
                            self.name, others_count + 1)
                    default['name'] = new_name
                    return super(Course, self).copy(default)

.. admonition:: Exercise 7 - Active objects – Default values
    :class: exercise

    Define the start_date default value as today. Add a field active in the
    class Session, and set the session as active by default.

    .. only:: solutions

        .. code-block:: python

            class Session(models.Model):
                _name = 'openacademuy.session'

                name = fields.Char(required=True)
                start_date = fields.Date( string="Start date", default=fields.Date.today)
                duration = fields.Float(string="Duration", digits=(6, 2))
                seats = fields.Integer(string="Number of seats")
                # is the record active in OpenERP
                active = fields.Boolean("Active", default=True)

        .. note::

            Odoo has built-in rules making fields with an ``active`` field set
            to ``False`` invisible.

Advanced Views
==============

List and trees
--------------

Lists include field elements, are created with type tree, and have a <tree>
parent element.

Attributes

* colors: list of colors mapped to Python conditions
* editable: top or bottom to allow in-place edit
* toolbar:set to True to display the top level of object hierarchies as a side toolbar
  (example: the menu)

Allowed elements

field, group, separator, tree, button, filter, newline


.. code-block:: xml

    <tree string="Idea Categories" toolbar="1" colors="blue:state==draft">
        <field name="name"/>
        <field name="state"/>
    </tree>

.. admonition:: Exercise 1 - List coloring
    :class: exercise

    Modify the Session tree view in such a way that sessions lasting less than
    5 days are colored blue, and the ones lasting more than 15 days are
    colored red.

    .. only:: solutions

        Modify the session tree view:

        .. literalinclude:: backend/exercisex1/openacademy.xml
            :language: xml
            :lines: 113-146

Calendars
---------

Used to display date fields as calendar events.

* color: name of field for color segmentation
* date_start: name of field containing event start date/time
* date_stop: name of field containing event stop date/time

field (to define the label for each calendar event)

.. code-block:: xml

    <calendar string="Ideas" date_start="invent_date" color="inventor_id">
        <field name="name"/>
    </calendar>

.. admonition:: Exercise 2 - Calendar view
    :class: exercise

    Add a Calendar view to the *Session* model enabling the user to view the
    events associated to the Open Academy.

    .. only:: solutions

        #. Add an ``end_date`` field computed from ``start_date`` and
           ``duration``

           .. literalinclude:: backend/exercisex2/course.py
               :lines: 33-34,43-65

           .. note:: the inverse function makes the field writable, and allows
                     moving the sessions (via drag and drop) in the calendar view

        #. Add a calendar view to the *Session* model

           .. literalinclude:: backend/exercisex2/openacademy.xml
                :language: xml
                :lines: 148-159

        #. And add the calendar view to the *Session* model's actions

            .. literalinclude:: backend/exercisex2/openacademy.xml
                :language: xml
                :lines: 161-166

Search views
------------

Search views are used to customize the search panel on top of list views, and
are declared with the search type, and a top-level <search> element.

After defining a search view with a unique id, add it to the action opening
the list view using the search_view_id field in its declaration.

.. code-block:: xml

    <search string="Ideas">
        <filter name="my_ideas" domain="[('inventor_id','=',uid)]"
                string="My Ideas" icon="terp-partner"/>
        <field name="name"/>
        <field name="description"/>
        <field name="inventor_id"/>
        <field name="country_id" widget="selection"/>
    </search>

The action record that opens such a view may initialize search fields by its
field context. The value of the field context is a Python dictionary that can modify the client's behavior. The keys of the dictionary are given a meaning depending on the following convention.

* The key 'default_foo' initializes the field 'foo' to the corresponding value
  in the form view.
* The key 'search_default_foo' initializes the field 'foo' to the
  corresponding value in the search view. Note that ``filter`` elements are
  like boolean fields.

.. admonition:: Exercise 3 - Search views
    :class: exercise

    Add a search view containing:

    #. a field to search the courses based on their title and
    #. a button to filter the courses of which the current user is the
       responsible. Make the latter selected by default.

    .. only:: solutions

        #. Add a search view for courses:

            .. literalinclude:: backend/exercisex3/openacademy.xml
                :language: xml
                :lines: 51-62

        #. Add the search view to the action:

            .. literalinclude:: backend/exercisex3/openacademy.xml
                :language: xml
                :lines: 69-83

Gantt
-----

Bar chart typically used to show project schedule (<gantt> parent element).

.. code-block:: xml

    <gantt string="Ideas" date_start="invent_date" color="inventor_id">
        <level object="idea.idea" link="id" domain="[]">
        <field name="inventor_id"/> </level>
    </gantt>

.. admonition:: Exercise 4 - Gantt charts
    :class: exercise

    Add a Gantt Chart enabling the user to view the sessions scheduling linked
    to the Open Academy module. The sessions should be grouped by instructor.

    .. only:: solutions

        #. Create a computed field expressing the session's duration in hours

           .. literalinclude:: backend/exercisex4/course.py
                :lines: 36-37,69-77

        #. Add the gantt view's definition, and add the gantt view to the
           *Session* model's action

           .. literalinclude:: backend/exercisex4/openacademy.xml
                :language: xml
                :lines: 181-199

Graph (charts)
--------------

.. todo:: look at graph view doc

.. code-block:: xml

    <graph string="Total idea score by Inventor" type="bar">
        <field name="inventor_id" />
        <field name="score" operator="+"/>
    </graph>

.. admonition:: Exercise 5 - Graph view
    :class: exercise

    Add a Graph view in the Session object that displays, for each course, the
    number of attendees under the form of a bar chart.

    .. only:: solutions

        #. Add the number of attendees as a computed field:

           .. literalinclude:: backend/exercisex5/course.py
                :lines: 39-41,82-85

           .. warning:: The **store** flag must be set as graphs are computed
                        directly from database storage.

        #. Then add the relevant view:

            .. literalinclude:: backend/exercisex5/openacademy.xml
                :language: xml
                :lines: 194-210

Kanban
------

Those views are available since OpenERP 6.1, and may be used to organize
tasks, production processes, etc. A kanban view presents a set of columns of
cards; each card represents a record, and columns represent the values of a
given field. For instance, project tasks may be organized by stage (each
column is a stage), or by responsible (each column is a user), and so on.

The following example is a simplification of the Kanban view of leads. The
view is defined with qweb templates, and can mix form elements with HTML
elements.

.. admonition:: Exercise 6 - Kanban view
    :class: exercise

    Add a Kanban view that displays sessions grouped by course (columns are
    thus courses).

    .. only:: solutions

        #. Add an integer ``color`` field to the *Session* model
        #. Add the kanban view and update the action

           .. literalinclude:: backend/exercisex6/openacademy.xml
                :language: xml
                :lines: 206-258

Workflows
=========

Workflows are models associated to business objects describing their dynamics.
Workflows are also used to track processes that evolve over time.

.. admonition:: Exercise 1 - Almost a workflow
    :class: exercise

    Add a state field that will be used for defining a “workflow” on the
    object Session. A session can have three possible states: Draft (default),
    Confirmed and Done. In the session form, add a (read-only) field to
    visualize the state, and buttons to change it. The valid transitions are:

    * Draft ➔ Confirmed
    * Confirmed ➔ Draft
    * Confirmed ➔ Done
    * Done ➔ Draft

    .. only:: solutions

        #. Add a new ``state`` field:

           .. literalinclude:: backend/exercisex7/course.py
                :lines: 42-46

        #. Add state-transitioning methods, those can be called from view
           buttons to change the record's state:

           .. literalinclude:: backend/exercisex7/course.py
                :lines: 48-58

        #. And add the relevant buttons to the session's form view:

           .. literalinclude:: backend/exercisex7/openacademy.xml
                :language: xml
                :lines: 102-151

*A sales order generates an invoice and a shipping order is an example of
workflow used in OpenERP*.

Workflows may be associated with any object in OpenERP, and are entirely
customizable. Workflows are used to structure and manage the lifecycles of
business objects and documents, and define transitions, triggers, etc. with
graphical tools. Workflows, activities (nodes or actions) and transitions
(conditions) are declared as XML records, as usual. The tokens that navigate
in workflows are called workitems.

.. admonition:: Exercise 2 - Dynamic workflow editor
    :class: exercise

    Using the workflow editor, create the same workflow as the one defined
    earlier for the Session object. Trans- form the Session form view such
    that the buttons change the state in the workflow.

    .. only:: solutions

        .. note::
            A workflow associated with a model is only created when the
            model's records are created. Thus there is no workflow instance
            associated with session instances created before the workflow's
            definition

        #. Create a workflow using the web client (:menuselection:`Settings
           --> Customization --> Workflows --> Workflows`), switch to the
           diagram view and add the relevant nodes and transition.

           A transition should be associated with the corresponding signal,
           and each activity (node) should call a function altering the
           session state according to the workflow state

        #. Alter the form view buttons to call use the workflow instead of the
           ``state`` field:

           .. literalinclude:: backend/exercisex8/openacademy.xml
                :language: xml
                :lines: 107-118

        #. If the function in the Draft activity is encoded, you can even
           remove the default state value in the *Session* model

           .. todo:: what?

        .. note::

            In order to check if instances of the workflow are correctly
            created with sessions, go to :menuselection:`Settings > Low Level
            Objects`

.. admonition:: Exercise 3 - Automatic transitions
    :class: exercise

    Add a transition Draft ! Confirmed that is triggered automatically when
    the number of attendees in a session is more than half the number of seats
    of that session.

    .. only:: solutions

        Add a transition between the *Draft* and *Confirmed* activities. It
        should not have a signal but it should have the condition
        ``seats_taken > 50``

.. admonition:: Exercise 4 - Server actions
    :class: exercise

    Create server actions and modify the previous workflow in order to
    re-create the same behaviour as previ- ously, but without using the Python
    methods of the Session class.

    .. only:: solutions

        ??

Security
========

Access control mechanisms must be configured to achieve a coherent security
policy.

Group-based access control mechanisms
-------------------------------------

Groups are created as normal records on the model “res.groups”, and granted
menu access via menu definitions. However even without a menu, objects may
still be accessible indirectly, so actual object-level permissions (read,
write, create, unlink) must be defined for groups. They are usually inserted
via CSV files inside modules. It is also possible to restrict access to
specific fields on a view or object using the field's groups attribute.

Access rights
-------------

Access rights are defined as records of the model “ir.model.access”. Each
access right is associated to a model, a group (or no group for global
access), and a set of permissions: read, write, create, unlink. Such access
rights are usually created by a CSV file named after its model:
``ir.model.access.csv``.

.. code-block:: text

    id,name,model_id/id,group_id/id,perm_read,perm_write,perm_create,perm_unlink
    access_idea_idea,idea.idea,model_idea_idea,base.group_user,1,1,1,0
    access_idea_vote,idea.vote,model_idea_vote,base.group_user,1,1,1,0

.. admonition:: Exercise 1 - Add access control through the OpenERP interface
    :class: exercise

    Create a new user “John Smith”. Then create a group
    “OpenAcademy / Session Read” with read access to the Session and Attendee
    objects.

    .. only:: solutions

        #. Create a new user *John Smith* through
           :menuselection:`Settings --> Users --> Users`
        #. Create a new group ``session_read`` through
           :menuselection:`Settings --> Users --> Groups`, it should have
           read access on the *Session* and *Attendee* models
        #. Edit *John Smith* to make them a member of ``session_read``
        #. Log in as *John Smith* to check the access rights are correct

.. admonition:: Exercise 2 - Add access control through data files in your module
    :class: exercise

    Using data files,

    * Create a group *OpenAcademy / Manager* with full access to all
      OpenAcademy models
    * Make *Session* and *Course* readable by all users

    .. only:: solutions

        #. Create a new file ``openacademy/security/security.xml``:

            .. code-block:: xml

                <openerp>
                  <data>
                    <record id="group_manager" model="res.groups">
                      <field name="name">OpenAcademy / Manager</field>
                    </record>
                  </data>
                </openerp>

        #. Create a new file ``openacademy/security/ir.model.access.csv``:

            .. code-block:: text

                id,name,model_id/id,group_id/id,perm_read,perm_write,perm_create,perm_unlink
                course_manager,course manager,model_openacademy_course,group_manager,1,1,1,1
                session_manager,session manager,model_openacademy_session,group_manager,1,1,1,1
                attendee_manager,attendee manager,model_openacademy_attendee,group_manager,1,1,1,1
                course_read_all,course all,model_openacademy_course,,1,0,0,0
                session_read_all,session all,model_openacademy_session,,1,0,0,0
                attendee_read_all,attendee all,model_openacademy_attendee,,1,0,0,0

        #. finally update ``openacademy/__openerp__.py`` with the new files:

            .. code-block:: python

                'data' : [
                    'security/security.xml',
                    'security/ir.model.access.csv',
                    'views/openacademy.xml',
                ],

Record rules
------------

A record rule restricts the access rights to a subset of records of the given
model. A rule is a record of the model “ir.rule”, and is associated to a
model, a number of groups (many2many field), permissions to which the
restriction applies, and a domain. The domain specifies to which records the
access rights are limited.

Here is an example of a rule that prevents the deletion of leads that are not
in state “cancel”. Notice that the value of the field “groups” must follow
the same convention as the method “write” of the ORM.

.. code-block:: xml

    <record id="delete_cancelled_only" model="ir.rule">
        <field name="name">Only cancelled leads may be deleted</field>
        <field name="model_id" ref="crm.model_crm_lead"/>
        <field name="groups" eval="[(4, ref('base.group_sale_manager'))]"/>
        <field name="perm_read" eval="0"/>
        <field name="perm_write" eval="0"/>
        <field name="perm_create" eval="0"/>
        <field name="perm_unlink" eval="1" />
        <field name="domain_force">[('state','=','cancel')]</field>
    </record>

.. admonition:: Exercise 4 - Record rule
    :class: exercise

    Add a record rule for the model Course and the group
    “OpenAcademy / Manager”, that restricts “write” and “unlink” accesses to
    the responsible of a course. If a course has no responsible, all users of
    the group must be able to modify it.

    .. only:: solutions

        Create a new rule in ``openacademy/security/security.xml``:

        .. code-block:: xml

            <record id="only_responsible_can_modify" model="ir.rule">
                <field name="name">Only Responsible can modify Course</field>
                <field name="model_id" ref="model_openacademy_course"/>
                <field name="groups" eval="[(4, ref('openacademy.group_manager'))]"/>
                <field name="perm_read" eval="0"/>
                <field name="perm_write" eval="1"/>
                <field name="perm_create" eval="0"/>
                <field name="perm_unlink" eval="1"/>
                <field name="domain_force">
                    ['|', ('responsible_id','=',False),
                          ('responsible_id','=',user.id)]
                </field>
            </record>

Internationalization
====================

Each module can provide its own translations within the i18n directory, by
having files named LANG.po where LANG is the locale code for the language, or
the language and country combination when they differ (e.g. pt.po or
pt_BR.po). Translations will be loaded automatically by OpenERP for all
enabled languages. Developers always use English when creating a module, then
export the module terms using OpenERP's gettext POT export feature
(Settings>Translations>Export a Translation File without specifying a
language), to create the module template POT file, and then derive the
translated PO files. Many IDE's have plugins or modes for editing and merging
PO/POT files.

.. tip:: The GNU gettext format (Portable Object) used by OpenERP is
         integrated into LaunchPad, making it an online collaborative
         translation platform.

.. code-block:: text

   |- idea/ # The module directory
      |- i18n/ # Translation files
         | - idea.pot # Translation Template (exported from OpenERP)
         | - fr.po # French translation
         | - pt_BR.po # Brazilian Portuguese translation
         | (...)

.. tip:: 

   By default OpenERP's POT export only extracts labels inside XML files or
   inside field definitions in Python code, but any Python string can be
   translated this way by surrounding it with the tools.translate._ method
   (e.g. _(‘Label') )

.. admonition:: Exercise 1 - Translate a module
   :class: exercise

   Choose a second language for your OpenERP installation. Translate your
   module using the facilities pro- vided by OpenERP.

   .. only:: solutions

        #. Create a directory ``openacademy/i18n/``
        #. Install whichever language you want (
           :menuselection:`Administration --> Translations --> Load an
           Official Translation`)
        #. Synchronize translatable terms (:menuselection`Administration -->
           Translations --> Application termsn --> Synchronize Translations`)
        #. Create a template translation file by exporting (
           :menuselection:`Administration --> Translations -> Import/Export
           --> Export Translation`) without specifying a language, save in
           ``openacademy/i18n/``
        #. Create a translation file by exporting (
           :menuselection:`Administration --> Translations --> Import/Export
           --> Export Translation`) and specifying a language. Save it in
           ``openacademy/i18n/``
        #. Open the exported translation file (with a basic text editor or a
           dedicated PO-file editor e.g. POEdit_ and translate the missing
           terms

           .. note::

               By default, Odoo's export only extracts labels inside XML
               records or Python field definitions, but arbitrary Python
               strings can be marked as translatable by calling
               :func:`openerp.tools.translate._` with them e.g. ``_("Label")``)

        #. Add ``from openerp.tools.translate import _`` to ``course.py`` and
           mark missing strings as translatable

           .. todo:: there isn't any!

        #. Repeat steps 3-6

        .. todo:: do we never reload translations?


Reporting
=========

Reports
-------

.. todo:: sle

Dashboards
----------

.. admonition:: Exercise 6 - Define a Dashboard
   :class: exercise

   Define a dashboard containing the graph view you created, the sessions
   calendar view and a list view of the courses (switchable to a form
   view). This dashboard should be available through a menuitem in the menu,
   and automatically displayed in the web client when the OpenAcademy main
   menu is selected.

   .. only:: solutions

        #. Create a ``openacademy/views/session_board.xml``. It should contain
           the board view, the actions referenced in that view, an action to
           open the dashboard and a re-definition of the main menu item to add
           the dashboard action

           .. code-block:: xml

                <?xml version="1.0"?>
                <openerp>
                  <data>
                    <record model="ir.actions.act_window" id="act_session_graph">
                      <field name="res_model">openacademy.session</field>
                      <field name="view_type">form</field>
                      <field name="view_mode">graph</field>
                      <field name="view_id"
                             ref="openacademy.openacademy_session_graph_view"/>
                    </record>
                    <record model="ir.actions.act_window" id="act_session_calendar">
                      <field name="res_model">openacademy.session</field>
                      <field name="view_type">form</field>
                      <field name="view_mode">calendar</field>
                      <field name="view_id" ref="openacademy.session_calendar_view"/>
                    </record>
                    <record model="ir.actions.act_window" id="act_course_list">
                      <field name="res_model">openacademy.course</field>
                      <field name="view_type">form</field>
                      <field name="view_mode">tree,form</field>
                    </record>
                    <record model="ir.ui.view" id="board_session_form">
                      <field name="name">Session Dashboard Form</field>
                      <field name="model">board.board</field>
                      <field name="type">form</field>
                      <field name="arch" type="xml">
                        <form string="Session Dashboard" version="7.0">
                          <board style="2-1">
                            <column>
                              <action
                                  string="Attendees by course"
                                  name="%(act_session_graph)d"
                                  colspan="4"
                                  height="150"
                                  width="510"/>
                              <action
                                  string="Sessions"
                                  name="%(act_session_calendar)d"
                                  colspan="4"/>
                            </column>
                            <column>
                              <action
                                  string="Courses"
                                  name="%(act_course_list)d" colspan="4"/>
                            </column>
                          </board>
                        </form>
                      </field>
                    </record>
                    <record model="ir.actions.act_window" id="open_board_session">
                      <field name="name">Session Dashboard</field>
                      <field name="res_model">board.board</field>
                      <field name="view_type">form</field>
                      <field name="view_mode">form</field>
                      <field name="usage">menu</field>
                      <field name="view_id" ref="board_session_form"/>
                    </record>
                    <menuitem id="openacademy_menu" name="OpenAcademy"
                              action="open_board_session"/>
                    <menuitem id="board.menu_dashboard" name="Dashboard" sequence="0"
                              parent="openacademy_all"/>
                    <menuitem
                        name="Session Dashboard" parent="board.menu_dashboard"
                        action="open_board_session"
                        sequence="1"
                        id="menu_board_session" icon="terp-graph"/>
                  </data>
                </openerp>

           .. note:: Available dashboard styles are ``1``, ``1-1``, ``1-2``,
                     ``2-1`` and ``1-1-1``


        #. Update ``openacademy/__openerp__.py`` to reference the new data
           file

WebServices
===========

The web-service module offer a common interface for all web-services :

• SOAP
• XML-RPC
• NET-RPC

Business objects can also be accessed via the distributed object
mechanism. They can all be modified via the client interface with contextual
views.

OpenERP is accessible through XML-RPC interfaces, for which libraries exist in
many languages.

XML-RPC Library
---------------

The following example is a Python program that interacts with an Odoo
server with the library xmlrpclib.

::

   import xmlrpclib
   # ... define HOST, PORT, DB, USER, PASS
   url = 'http://%s:%d/xmlrpc/common' % (HOST,PORT) sock = xmlrpclib.ServerProxy(url)
   uid = sock.login(DB,USER,PASS)
   print "Logged in as %s (uid:%d)" % (USER,uid)
   # Create a new idea
   url = 'http://%s:%d/xmlrpc/object' % (HOST,PORT) sock = xmlrpclib.ServerProxy(url)
   args = {
       'name' : 'Another idea',
       'description' : 'This is another idea of mine',
       'inventor_id': uid,
   }
   idea_id = sock.execute(DB,uid,PASS,'idea.idea','create',args)

.. admonition:: Exercise 1 - Add a new service to the client
   :class: exercise

   Write a Python program able to send XML-RPC requests to a PC running
   Odoo (yours, or your instructor's). This program should display all
   the sessions, and their corresponding number of seats. It should also
   create a new session for one of the courses.

   .. only:: solutions

        .. code-block:: python

            import xmlrpclib
            HOST='192.168.0.44'
            PORT=8069
            DB='openacademy'
            USER='admin'
            PASS='admin'
            url = 'http://%s:%d/xmlrpc/' % (HOST,PORT)
            common_proxy = xmlrpclib.ServerProxy(url+'common')
            object_proxy = xmlrpclib.ServerProxy(url+'object')
            def execute(\*args):
                    return object_proxy.execute(DB,uid,PASS,*args)
            # 1. Login
            uid = common_proxy.login(DB,USER,PASS)
            print "Logged in as %s (uid:%d)" % (USER,uid)
            # 2. Read the sessions
            session_ids = execute('openacademy.session','search',[])
            sessions = execute('openacademy.session','read',session_ids, ['name','seats'])
            for session in sessions :
                print "Session name :%s (%s seats)" % (session['name'], session['seats'])
            # 3.create a new session
            session_id = execute('openacademy.session', 'create',
                                 {'name' : 'My session',
                                  'course_id' : 2, })

        Instead of using a hard-coded course id, the code can look up a course
        by name::

            # 3.create a new session for the "Functional" course
            course_id = execute('openacademy.course', 'search', [('name','ilike','Functional')])[0]
            session_id = execute('openacademy.session', 'create',
                                 {'name' : 'My session',
                                  'course_id' : course_id, })

.. note:: there are also a number of high-level APIs in various languages to
          access Odoo systems without *explicitly* going through XML-RPC e.g.

    * https://github.com/akretion/ooor
    * https://github.com/syleam/openobject-library
    * https://github.com/nicolas-van/openerp-client-lib
    * https://pypi.python.org/pypi/oersted/

.. [#autofields] it is possible to :attr:`disable the creation of some
                 <openerp.models.Model._log_access>`

.. _database index:
    http://use-the-index-luke.com/sql/preface

.. _POEdit: http://poedit.net

.. _PostgreSQL's documentation:
    http://www.postgresql.org/docs/9.3/static/ddl-constraints.html

.. _XPath: http://w3.org/TR/xpath
