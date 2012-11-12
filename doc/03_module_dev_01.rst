Module structure
================

A module can contain the following elements:

 - **Business object** : declared as Python classes extending the OpenObject c
   lass osv.Model, the persistence of these resource is completly managed 
   by OpenObject,
 - **Data** : XML/CSV files with meta-data (views and workflows declaration), 
   configuration data (modules parametrization) and demo data (optional but 
   recommended for testing),
 - **Wizards** : stateful interactive forms used to assist users, often available 
   as contextual actions on resources,
 - **Reports** : RML (XML format). MAKO or OpenOffice report templates, to be 
   merged with any kind of business data, and generate HTML, ODT or PDF reports.

.. figure:: _static/03_module_gen_view.png
   :width: 75%
   :alt: Module composition
   :align: center
   
   Module composition

Each module is contained in its own directory within either the server/bin/addons 
directory or another directory of addons, configured in server installation.
To create a new module, the following steps are required:

 - create a ``my_module`` subdirectory in the source/addons directory
 - create the module description file ``__init__.py``
 - create the module declaration file ``__openerp__.py``
 - create **Python** files containing **objects**
 - create **.xml files** holding module data such as views, menu entries 
   or demo data
 - optionally create **reports**, **wizards** or **workflows**

Description file __init__.py
++++++++++++++++++++++++++++

The ``__init__.py`` file is the Python module descriptor, because an OpenERP 
module is also a regular Python module. Like any Python module, it is executed 
at program start. It needs to import the Python files that need to be loaded.

It contains the importation instruction applied to all Python files of the 
module, without the .py extension. For example, if a module contains a single 
python file named ``mymodule.py``, the file should look like:

    import module

Declaration file __openerp__.py
+++++++++++++++++++++++++++++++

In the created module directory, you must add a **__openerp__.py** file.
This file, which must be in Python format, is responsible to

   1. determine the *XML files that will be parsed* during the initialization
      of the server, and also to
   2. determine the *dependencies* of the created module.

This file must contain a Python dictionary with the following values:

::

  name             The (Plain English) name of the module.
  version          The version of the module.
  description      The module description (text).
  author           The author of the module.
  website          The website of the module.
  license          The license of the module (default:GPL-2).
  depends          List of modules on which this module depends. The base 
                   module must almost always be in the dependencies because 
                   some necessary data for the views, reports, ... are in 
                   the base module.
  init_xml         List of .xml files to load when the server is launched 
                   with the "--init=module" argument. Filepaths must be 
                   relative to the directory where the module is. OpenERP 
                   XML file format is detailed in this section.
  update_xml       List of .xml files to load when the server is launched with 
                   the "--update=module" launched. Filepaths must be relative 
                   to the directory where the module is. Files in **update_xml** 
                   concern: views, reports and wizards.
  installable      True or False. Determines whether the module is installable 
                   or not.
  auto_install     True or False (default: False). If set to ``True``, the
                   module is a link module. It will be installed as soon
                   as all its dependencies are installed.

For the ``my_module`` module, here is an example of ``__openerp__.py``
declaration file:

.. code-block:: python

    {
        'name' : "My Module",
        'version' : "1.0",
        'author' : "OpenERP",
        'category' : "Tools",
        'depends' : ['base',],
        'init_xml' : [],
        'demo_xml' : [
            'module_demo.xml'
        ],
        'update_xml' : [
            'module_view.xml',
            'data/module_data.xml',
            'report/module_report.xml',
            'wizard/module_wizard.xml',
        ],
        'installable': True,
        'auto_install': False,
    }

The files that must be placed in init_xml are the ones that relate to the
workflow definition, data to load at the installation of the software and
the data for the demonstrations.


XML Files
+++++++++

XML files located in the module directory are used to modify the structure of
the database. They are used for many purposes, among which we can cite :

    * initialization and demonstration data declaration,
    * views declaration,
    * reports declaration,
    * wizards declaration,
    * workflows declaration.

General structure of OpenERP XML files is more detailed in the 
:ref:`xml-serialization` section. Look here if you are interested in learning 
more about *initialization* and *demonstration data declaration* XML files. The 
following section are only related to XML specific to *actions, menu entries, 
reports, wizards* and *workflows* declaration.


Objects
+++++++

All OpenERP resources are objects: menus, actions, reports, invoices, partners, ... OpenERP is based on an object relational mapping of a database to control the information. Object names are hierarchical, as in the following examples:

    * account.transfer : a money transfer
    * account.invoice : an invoice
    * account.invoice.line : an invoice line

Generally, the first word is the name of the module: account, stock, sale.

Other advantages of an ORM;

    * simpler relations : invoice.partner.address[0].city
    * objects have properties and methods: invoice.pay(3400 EUR),
    * inheritance, high level constraints, ...

It is easier to manipulate one object (example, a partner) than several tables (partner address, categories, events, ...)


.. figure::  images/pom_3_0_3.png
   :scale: 50
   :align: center

   *The Physical Objects Model of [OpenERP version 3.0.3]*


PostgreSQL and ORM
------------------

The ORM of OpenERP is constructed over PostgreSQL. It is thus possible to
query the object used by OpenERP using the object interface or by directly
using SQL statements.

But it is dangerous to write or read directly in the PostgreSQL database, as
you will shortcut important steps like constraints checking or workflow
modification.

.. note::

    The Physical Database Model of OpenERP

Pre-Installed Data
------------------

Data can be inserted or updated into the PostgreSQL tables corresponding to the
OpenERP objects using XML files. The general structure of an OpenERP XML file
is as follows:

.. code-block:: xml

   <?xml version="1.0"?>
   <openerp>
     <data>
       <record model="model.name_1" id="id_name_1">
         <field name="field1">
           "field1 content"
         </field>
         <field name="field2">
           "field2 content"
         </field>
         (...)
       </record>
       <record model="model.name_2" id="id_name_2">
           (...)
       </record>
       (...)
     </data>
   </openerp>

Fields content are strings that must be encoded as *UTF-8* in XML files.

Let's review an example taken from the OpenERP source (base_demo.xml in the base module):

.. code-block:: xml

       <record model="res.company" id="main_company">
           <field name="name">Tiny sprl</field>
           <field name="partner_id" ref="main_partner"/>
           <field name="currency_id" ref="EUR"/>
       </record>

.. code-block:: xml

       <record model="res.users" id="user_admin">
           <field name="login">admin</field>
           <field name="password">admin</field>
           <field name="name">Administrator</field>
           <field name="signature">Administrator</field>
           <field name="action_id" ref="action_menu_admin"/>
           <field name="menu_id" ref="action_menu_admin"/>
           <field name="address_id" ref="main_address"/>
           <field name="groups_id" eval="[(6,0,[group_admin])]"/>
           <field name="company_id" ref="main_company"/>
       </record>

This last record defines the admin user :

    * The fields login, password, etc are straightforward.
    * The ref attribute allows to fill relations between the records :

.. code-block:: xml

       <field name="company_id" ref="main_company"/>

The field **company_id** is a many-to-one relation from the user object to the company object, and **main_company** is the id of to associate.

    * The **eval** attribute allows to put some python code in the xml: here the groups_id field is a many2many. For such a field, "[(6,0,[group_admin])]" means : Remove all the groups associated with the current user and use the list [group_admin] as the new associated groups (and group_admin is the id of another record).

    * The **search** attribute allows to find the record to associate when you do not know its xml id. You can thus specify a search criteria to find the wanted record. The criteria is a list of tuples of the same form than for the predefined search method. If there are several results, an arbitrary one will be chosen (the first one):

.. code-block:: xml

       <field name="partner_id" search="[]" model="res.partner"/>

This is a classical example of the use of **search** in demo data: here we do not really care about which partner we want to use for the test, so we give an empty list. Notice the **model** attribute is currently mandatory.

Record Tag
//////////

**Description**

The addition of new data is made with the record tag. This one takes a mandatory attribute : model. Model is the object name where the insertion has to be done. The tag record can also take an optional attribute: id. If this attribute is given, a variable of this name can be used later on, in the same file, to make reference to the newly created resource ID.

A record tag may contain field tags. They indicate the record's fields value. If a field is not specified the default value will be used.

**Example**

.. code-block:: xml

    <record model="ir.actions.report.xml" id="l0">
         <field name="model">account.invoice</field>
         <field name="name">Invoices List</field>
         <field name="report_name">account.invoice.list</field>
         <field name="report_xsl">account/report/invoice.xsl</field>
         <field name="report_xml">account/report/invoice.xml</field>
    </record>

Field tag
/////////

The attributes for the field tag are the following:

name : mandatory
  the field name

eval : optional
  python expression that indicating the value to add
  
ref
  reference to an id defined in this file

model
  model to be looked up in the search

search
  a query

Function tag
////////////

A function tag can contain other function tags.

model : mandatory
  The model to be used

name : mandatory
  the function given name

eval
  should evaluate to the list of parameters of the method to be called, excluding cr and uid

**Example**

.. code-block:: xml

    <function model="ir.ui.menu" name="search" eval="[[('name','=','Operations')]]"/>

Getitem tag
///////////

Takes a subset of the evaluation of the last child node of the tag.

type : mandatory
  int or list

index : mandatory
  int or string (a key of a dictionary)

**Example**

Evaluates to the first element of the list of ids returned by the function node

.. code-block:: xml

    <getitem index="0" type="list">
        <function model="ir.ui.menu" name="search" eval="[[('name','=','Operations')]]"/>
    </getitem>

i18n
""""

Improving Translations
//////////////////////

.. describe:: Translating in launchpad

Translations are managed by
the `Launchpad Web interface <https://translations.launchpad.net/openobject>`_. Here, you'll
find the list of translatable projects.

Please read the `FAQ <https://answers.launchpad.net/rosetta/+faqs>`_ before asking questions.

.. describe:: Translating your own module

.. versionchanged:: 5.0

Contrary to the 4.2.x version, the translations are now done by module. So,
instead of an unique ``i18n`` folder for the whole application, each module has
its own ``i18n`` folder. In addition, OpenERP can now deal with ``.po`` [#f_po]_
files as import/export format. The translation files of the installed languages
are automatically loaded when installing or updating a module. OpenERP can also
generate a .tgz archive containing well organised ``.po`` files for each selected
module.

.. [#f_po] http://www.gnu.org/software/autoconf/manual/gettext/PO-Files.html#PO-Files

Process
"""""""

Defining the process
////////////////////

Through the interface and module recorder.
Then, put the generated XML in your own module.

Views
"""""

Technical Specifications - Architecture - Views
///////////////////////////////////////////////

Views are a way to represent the objects on the client side. They indicate to the client how to lay out the data coming from the objects on the screen.

There are two types of views:

    * form views
    * tree views

Lists are simply a particular case of tree views.

A same object may have several views: the first defined view of a kind (*tree, form*, ...) will be used as the default view for this kind. That way you can have a default tree view (that will act as the view of a one2many) and a specialized view with more or less information that will appear when one double-clicks on a menu item. For example, the products have several views according to the product variants.

Views are described in XML.

If no view has been defined for an object, the object is able to generate a view to represent itself. This can limit the developer's work but results in less ergonomic views.


Usage example
/////////////

When you open an invoice, here is the chain of operations followed by the client:

    * An action asks to open the invoice (it gives the object's data (account.invoice), the view, the domain (e.g. only unpaid invoices) ).
    * The client asks (with XML-RPC) to the server what views are defined for the invoice object and what are the data it must show.
    * The client displays the form according to the view

.. figure::  images/arch_view_use.png
   :scale: 50
   :align: center

To develop new objects
//////////////////////

The design of new objects is restricted to the minimum: create the objects and optionally create the views to represent them. The PostgreSQL tables do not have to be written by hand because the objects are able to automatically create them (or adapt them in case they already exist).

Reports
"""""""

OpenERP uses a flexible and powerful reporting system. Reports are generated either in PDF or in HTML. Reports are designed on the principle of separation between the data layer and the presentation layer.

Reports are described more in details in the `Reporting <http://openobject.com/wiki/index.php/Developers:Developper%27s_Book/Reports>`_ chapter.


Workflow
""""""""

The objects and the views allow you to define new forms very simply, lists/trees and interactions between them. But that is not enough, you must define the dynamics of these objects.

A few examples:

    * a confirmed sale order must generate an invoice, according to certain conditions
    * a paid invoice must, only under certain conditions, start the shipping order

The workflows describe these interactions with graphs. One or several workflows may be associated to the objects. Workflows are not mandatory; some objects don't have workflows.

Below is an example workflow used for sale orders. It must generate invoices and shipments according to certain conditions.

.. figure::  images/arch_workflow_sale.png
   :scale: 85
   :align: center


In this graph, the nodes represent the actions to be done:

    * create an invoice,
    * cancel the sale order,
    * generate the shipping order, ...

The arrows are the conditions;

    * waiting for the order validation,
    * invoice paid,
    * click on the cancel button, ...

The squared nodes represent other Workflows;

    * the invoice
    * the shipping



Appendix
+++++++++

Configure addons locations
--------------------------

By default, the only directory of addons known by the server is server/bin/addons. 
It is possible to add new addons by

 - copying them in server/bin/addons, or creating a symbolic link to each 
   of them in this directory, or
 - specifying another directory containing addons to the server. The later 
   can be accomplished either by running the server with the ``--addons-path=`` 
   option, or by configuring this option in the openerp_serverrc file, 
   automatically generated under Linux in your home directory by the 
   server when executed with the ``--save`` option. You can provide several 
   addons to the ``addons_path`` = option, separating them using commas.
