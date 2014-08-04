=======
Backend
=======

Build an Odoo module
====================

Composition of a module
-----------------------

.. TODO: graph? Physical / logical composition?

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

.. fixme: redundant with same section in web howto, use include? separate
          intro to modules?

Each module is a directory within a *module directory*. Module directories
are specified by using the :option:`--addons-path <odoo.py --addons-path>`
option.

.. reference for config file?

.. tip:: most command-line options can also be set using a configuration file

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

.. todo:: Exercise 1 — module creation

    Create an empty module Open Academy, install it in Odoo

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

.. todo:: Exercise 2 — define a model

    Define a new data model *Course* in the *openacademy* module. A course
    has a name, or "title", and a description. All courses must have a name.

.. FIXME: does this really make sense as part of the ORM chapter?

Actions and Menus
-----------------

Actions are declared as regular records and can be triggered in three ways:

#. by clicking on menu items (linked to specific actions)
#. by clicking on buttons in views (if these are connected to actions)
#. as contextual actions on object

.. FIXME: maybe <record> should be introduced before shortcuts?

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

    The action must be declared before its corresponding menu in the XML
    file.

    Data files are executed sequentially, the action's ``id`` must be present
    in the database before the menu can be created.

.. todo:: Exercise 3 — Define new menu entries

    Define new menu entries to access courses and sessions under the
    OpenAcademy menu entry. A user should be able to

    #) display a list of all the courses
    #) create/modify courses

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

.. danger::

    The view's content is XML. The ``arch`` field must thus be declared as
    ``type="xml"`` to be parsed correctly.

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

.. todo:: Exercise 1 - Customise form view using XML

    Create your own form view for the Course object. Data displayed should be:
    the name and the description of the course.

.. todo:: Exercise 2 - Notebooks

    In the Course form view, put the description field under a tab, such that
    it will be easier to add other tabs later, containing additional
    information.

Relations between objects
=========================

.. todo:: Exercise 1 — create models

    Create models for *sessions* and *attendees*, add an action and a menu
    item to display the sessions.

    A session has a name, a start date, a duration and a number of seats.

    An attendee has a name.

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

.. todo:: Exercise 2 — Relations many2one

    Using a many2one, modify the *Course*, *Session* and *Attendee* models to
    reflect their relation with one another

    <insert schema here>

.. todo:: Exercise 3 — Inverse o2m

    Using the inverse relational field o2m, modify the models to reflect their
    inverse relations

.. todo:: Exercise 4 — Views modification

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

.. todo:: Exercise 2 — relational fields

    When selecting the instructor for a *Session*, only instructors (partners
    with ``is_instructor`` set to ``True``) should be visible.

.. todo:: Exercise 3 — relational fields bis

    Create new partner categories *Teacher / Level 1* and *Teacher / Level 2*.
    The instructor for a session can be either an instructor or a teacher
    (of any level).

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

.. todo:: Exercise 1 — alter existing content

    * Using model inheritance, modify the existing *Partner* model to add an
      ``is_instructor`` boolean field, and a list of the sessions for which
      the partner is the instructor
    * Using view inheritance, display these fields in the partner form view

Computed fields
===============

So far fields have been stored directly in and retrieved directly from the
database. Fields can also be *computed*. In that case, the field's value is
not retrieved from the database but computed on-the-fly by calling a method
of the model object.

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
            self.name = str(random.randint(1, 1e6)

.. todo:: Exercise 1: computed fields

    * Add the percentage of filled seats to the *Session* model
    * Display that field in the tree and form views
    * Display the field as a progress bar

Onchange
========

.. todo:: no idea how onchange works in new API

.. todo:: Exercise 1 — onchange methods

    Modify the Session form view and the Session model so the
    percentage of taken seats refreshes whenever the number of available seats
    or the number of attendees changes, without having to save the
    modifications.

.. todo:: Exercise 2 — warning

    Modify the *onchange* to raise a warning when the number of available
    seats is negative.

Model invariants
================

* :attr:`~openerp.models.Model._constraints`
* :attr:`~openerp.models.Model._sql_constraints`

.. todo:: Exercise 4 - Add Python constraints

    Add a constraint that checks that the instructor is not present in the attendees of his/her own session.

.. todo:: Exercise 5 - Add SQL constraints

    With the help of `PostgreSQL's documentation`_ , add the following
    constraints:

    #. CHECK that the course description and the course title are not the same
    #. Make the Course's name UNIQUE
    #. Make sure the Attendee table can not contain the same partner for the
       same session multiple times (UNIQUE on pairs)

.. todo:: Exercise 6 - Add a duplicate option

    Since we added a constraint for the Course name uniqueness, it is not possible to use the “duplicate” function anymore (Form > Duplicate). Re-implement your own “copy” method which allows to duplicate the Course object, changing the original name into “Copy of [original name]”.

.. todo:: Exercise 7 - Active objects – Default values

    Define the start_date default value as today. Add a field active in the
    class Session, and set the session as active by default.

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

.. todo:: Exercise 1 - List coloring

    Modify the Session tree view in such a way that sessions lasting less than
    5 days are colored blue, and the ones lasting more than 15 days are
    colored red.

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

.. todo:: Exercise 2 - Calendar view

    Add a Calendar view to the *Session* model enabling the user to view the
    events associated to the Open Academy.

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

.. todo:: Exercise 3 - Search views

    Add a search view containing:

    #. a field to search the courses based on their title and
    #. a button to filter the courses of which the current user is the
       responsible. Make the latter selected by default.

Gantt
-----

Bar chart typically used to show project schedule (<gantt> parent element).

.. code-block:: xml

    <gantt string="Ideas" date_start="invent_date" color="inventor_id">
        <level object="idea.idea" link="id" domain="[]">
        <field name="inventor_id"/> </level>
    </gantt>

.. todo:: Exercise 4 - Gantt charts

    Add a Gantt Chart enabling the user to view the sessions scheduling linked
    to the Open Academy module. The sessions should be grouped by instructor.

Graph (charts)
--------------

.. code-block:: xml

    <graph string="Total idea score by Inventor" type="bar">
        <field name="inventor_id" />
        <field name="score" operator="+"/>
    </graph>

.. todo:: Exercise 5 - Graph view

    Add a Graph view in the Session object that displays, for each course, the
    number of attendees under the form of a bar chart.

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

.. todo:: Exercise 6 - Kanban view

    Add a Kanban view that displays sessions grouped by course (columns are
    thus courses).

Workflows
=========

Workflows are models associated to business objects describing their dynamics.
Workflows are also used to track processes that evolve over time.

.. todo:: Exercise 1 - Almost a workflow

    Add a state field that will be used for defining a “workflow” on the
    object Session. A session can have three possible states: Draft (default),
    Confirmed and Done. In the session form, add a (read-only) field to
    visualize the state, and buttons to change it. The valid transitions are:

    * Draft ➔ Confirmed
    * Confirmed ➔ Draft
    * Confirmed ➔ Done
    * Done ➔ Draft

*A sales order generates an invoice and a shipping order is an example of
workflow used in OpenERP*.

Workflows may be associated with any object in OpenERP, and are entirely
customizable. Workflows are used to structure and manage the lifecycles of
business objects and documents, and define transitions, triggers, etc. with
graphical tools. Workflows, activities (nodes or actions) and transitions
(conditions) are declared as XML records, as usual. The tokens that navigate
in workflows are called workitems.

.. todo:: Exercise 2 - Dynamic workflow editor

    Using the workflow editor, create the same workflow as the one defined
    earlier for the Session object. Trans- form the Session form view such
    that the buttons change the state in the workflow.

.. note::

    A workflow associated to a session is created during the creation of that
    session. There is therefore no workflow instance associated to session
    instances created before the definition of the workflow.

.. todo:: Exercise 3 - Automatic transitions

    Add a transition Draft ! Confirmed that is triggered automatically when
    the number of attendees in a session is more than half the number of seats
    of that session.

.. todo:: Exercise 4 - Server actions

    Create server actions and modify the previous workflow in order to
    re-create the same behaviour as previ- ously, but without using the Python
    methods of the Session class.

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

.. todo:: Exercise 1 - Add access control through the OpenERP interface

    Create a new user “John Smith”. Then create a group
    “OpenAcademy / Session Read” with read access to the Session and Attendee
    objects.

.. todo:: Exercise 2 - Add access control through data files in your module

    Using an XML data file, create a group “OpenAcademy / Manager”, with no
    access rights defined yet (just create an empty group).

.. todo:: Exercise 3 - Add access control through data files in your module

    Use a CSV file to add read, write, creation and deletion rights on the
    objects Course, Session and Attendees to the group OpenAcademy / Manager.
    You can also create rights associated to no group, such as a read only
    access on Course and a read only access on Session.

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

.. todo:: Exercise 4 - Record rule

    Add a record rule for the model Course and the group
    “OpenAcademy / Manager”, that restricts “write” and “unlink” accesses to
    the responsible of a course. If a course has no responsible, all users of
    the group must be able to modify it.

Wizards
=======

Wizard objects (models.TransientModel)
--------------------------------------

Wizards describe stateful interactive sessions with the user (or dialog boxes)
through dynamic forms. A wizard is built simply by defining a model that
extends the class “osv.TransientModel” instead of “osv.Model”. The class
“osv.TransientModel” extends “osv.Model” and reuse all its existing
mechanisms, with the following particularities:

* Wizard records are not meant to be persistent; they are automatically
  deleted from the database after a certain time. This is why they are called
  “transient”.
* Wizard models do not require explicit access rights: users have all
  permissions on wizard records.
* Wizard records may refer to regular records or wizard records through
  many2one fields, but regular records cannot refer to wizard records through
  a many2one field.

We want to create a wizard that allow users to create attendees for a
particular session, or for a list of sessions at once. In a first step, the
wizard will work for a single session.

.. todo:: Exercise 1 - Define the wizard class

   Create a wizard model (inheriting from osv.TransientModel) with a many2one
   relationship with the Session object and a one2many relationship with an
   Attendee object (wizard object, too). The new Attendee object has a name
   field and a many2one relationship with the Partner object. Define the class
   CreateAttendeeWizard and implement its structure.


Wizard execution
----------------

Wizards are launched by “ir.actions.act_window” records, with the field
“target” set to value “new”. The latter opens the wizard view into a popup
window. The action is triggered by a menu item.

There is another way to launch the wizard: using an “ir.actions.act_window”
record like above, but with an extra field “src_model” that specifies in the
context of which model the action is available. The wizard will appear in the
contextual actions of the model, on the right-hand side bar. Because of some
internal hooks in the ORM, such an action is declared in XML with the tag
“act_window”.

.. code-block:: xml

   <act_window id="session_create_attendee_wizard"
               name="Add Attendees"
               src_model="context_model_name"
               res_model="wizard_model_name"
               view_mode="form"
               target="new"
               key2="client_action_multi"/>

.. note:: 

   The field “key2” defines a kind of action category. Its possible values
   are: “client_action_multi” (typically for wizards), “client_print_multi”
   (typically for reports), and “client_action_relate” (typically for related
   views).

.. todo:: Exercise 2 - Make the wizard available through a menuitem

   Create a menuitem and the necessary action to use the wizard.

Wizard views
------------

Wizards use regular views and their buttons may use the attribute
``special=”cancel”`` to close the wizard window without saving.

.. code-block:: xml

   <button string="Do it!" type="object" name="some_action"/>
   <button string="Cancel" special="cancel"/>

.. todo:: Exercise 3 - Customise the form view

   Customise the form view in order to show all the fields of the class.

.. todo:: Exercise 4 - Create methods

   Create the method action_add_attendee in your class CreateAttendeeWizard,
   implement it, and add a button in the form view to call it. Add also a
   button “Cancel” that closes the wizard window.

.. todo:: Exercise 5 - Bind the wizard to the context bar

   Bind the wizard to the context bar of the session model.

   .. tip:: use the argument “context” to define the current session as
            default value for the field “session_id” in the wizard.

.. todo:: Extra Exercise - Wizard on multiple records

   Make the wizard able to add attendees to several sessions at once.

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

.. todo:: Exercise 1 - Translate a module

   Choose a second language for your OpenERP installation. Translate your
   module using the facilities pro- vided by OpenERP.

Reporting
=========

Reports
-------

Dashboards
----------

.. todo:: Exercise 6 - Define a Dashboard

   Define a dashboard containing the graph view you created, the sessions
   calendar view and a list view of the courses (switchable to a form
   view). This dashboard should be available through a menuitem in the menu,
   and automatically displayed in the web client when the OpenAcademy main
   menu is selected.

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

The following example is a Python program that interacts with an OpenERP
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

.. todo:: Exercise 1 - Add a new service to the client

   Write a Python program able to send XML-RPC requests to a PC running
   OpenERP (yours, or your instruc- tor's). This program should display all
   the sessions, and their corresponding number of seats. It should also
   create a new session for one of the courses.

13.2 OpenERP Client Library
---------------------------

The OpenERP Client Library (http://pypi.python.org/pypi/openerp-client-lib) is
a Python library to communicate with an OpenERP server using its web services
in an user-friendly way. It provides simple wrapper objects to abstract the
bare XML-RPC calls.

If necessary, install the library:

.. code-block:: console

   $ sudo easy_install openerp-client-lib

The following Python program is equivalent to the example above.

::

   import openerplib
   # ... define HOST, PORT, DB, USER, PASS
   connection = openerplib.get_connection(hostname=HOST, port=PORT, database=DB,
   login=USER, password=PASS)
   print "Logged in as %s (uid:%d)" % (connection.login, connection.user_id)
   connection.check_login()
   # create an idea
   idea_model = connection.get_model('idea.idea')
   values = {
       'name': 'Another idea',
       'description': 'This is another idea of mine',
       'inventor_id': connection.user_id,
   }
   idea_id = idea_model.create(values)

.. todo:: Exercise 2 - Add a new service to the client

   Do the same as Exercise 1, but this time using openerplib.

.. [#autofields] it is possible to :attr:`disable the creation of some
                 <openerp.models.Model._log_access>`

.. _database index:
    http://use-the-index-luke.com/sql/preface

.. _PostgreSQL's documentation:
    http://www.postgresql.org/docs/9.3/static/ddl-constraints.html

.. _XPath: http://w3.org/TR/xpath
