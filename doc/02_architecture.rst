========================================
Architecture
========================================

MVC architecture
================

According to `Wikipedia <http://en.wikipedia.org/wiki/Model-view-controller>`_, "a Model-view-controller (MVC) is an architectural pattern used in software engineering". In complex computer applications presenting lots of data to the user, one often wishes to separate data (model) and user interface (view) concerns. Changes to the user interface does therefore not impact data management, and data can be reorganized without changing the user interface. The model-view-controller solves this problem by decoupling data access and business logic from data presentation and user interaction, by introducing an intermediate component: the controller.

.. figure::  images/MVCDiagram.png
   :scale: 100
   :align: center

   MVC Diagram

For example in the diagram above, the solid lines for the arrows starting from the controller and going to both the view and the model mean that the controller has a complete access to both the view and the model. The dashed line for the arrow going from the view to the controller means that the view has a limited access to the controller. The reasons of this design are :

    * From **View** to **Model** : the model sends notification to the view when its data has been modified in order the view to redraw its content. The model doesn't need to know the inner workings of the view to perform this operation. However, the view needs to access the internal parts of the model.
    * From **View** to **Controller** : the reason why the view has limited access to the controller is because the dependencies from the view to the controller need to be minimal: the controller can be replaced at any moment. 

MVC Model in OpenERP
--------------------

In OpenERP, we can apply this model-view-controller semantic with

    * model : The PostgreSQL tables.
    * view : views are defined in XML files in OpenERP.
    * controller : The objects of OpenERP. 


MVCSQL
------

Example 1
+++++++++

Suppose sale is a variable on a record of the sale.order object related to the 'sale_order' table. You can acquire such a variable doing this.::

    sale = self.browse(cr, uid, ID)

(where cr is the current row, from the database cursor, uid is the current user's ID for security checks, and ID is the sale order's ID or list of IDs if we want more than one)

Suppose you want to get: the country name of the first contact of a partner related to the ID sale order. You can do the following in OpenERP::

    country_name = sale.partner_id.address[0].country_id.name

If you want to write the same thing in traditional SQL development, it will be in python: (we suppose cr is the cursor on the database, with psycopg)

.. code-block:: python

    cr.execute('select partner_id from sale_order where id=%d', (ID,))
    partner_id = cr.fetchone()[0]
    cr.execute('select country_id from res_partner_address where partner_id=%d', (partner_id,))
    country_id = cr.fetchone()[0]
    cr.execute('select name from res_country where id=%d', (country_id,))
    del partner_id
    del country_id
    country_name = cr.fetchone()[0]

Of course you can do better if you develop smartly in SQL, using joins or subqueries. But you have to be smart and most of the time you will not be able to make such improvements:

    * Maybe some parts are in others functions
    * There may be a loop in different elements
    * You have to use intermediate variables like country_id

The first operation as an object call is much better for several reasons:

    * It uses objects facilities and works with modules inheritances, overload, ...
    * It's simpler, more explicit and uses less code
    * It's much more efficient as you will see in the following examples
    * Some fields do not directly correspond to a SQL field (e.g.: function fields in Python)


Prefetching
+++++++++++

Suppose that later in the code, in another function, you want to access the name of the partner associated to your sale order. You can use this::

    partner_name = sale.partner_id.name

And this will not generate any SQL query as it has been prefetched by the object relational mapping engine of OpenERP.


Loops and special fields
++++++++++++++++++++++++

Suppose now that you want to compute the totals of 10 sales order by countries. You can do this in OpenERP within a OpenERP object:

.. code-block:: python

    def get_totals(self, cr, uid, ids):
       countries = {}
       for sale in self.browse(cr, uid, ids):
          country = sale.partner_invoice_id.country
          countries.setdefault(country, 0.0)
          countries[country] += sale.amount_untaxed
       return countries

And, to print them as a good way, you can add this on your object:

.. code-block:: python

    def print_totals(self, cr, uid, ids):
       result = self.get_totals(cr, uid, ids)
       for country in result.keys():
          print '[%s] %s: %.2f' (country.code, country.name, result[country])

The 2 functions will generate 4 SQL queries in total ! This is due to the SQL engine of OpenERP that does prefetching, works on lists and uses caching methods. The 3 queries are:

   1. Reading the sale.order to get ID's of the partner's address
   2. Reading the partner's address for the countries
   3. Calling the amount_untaxed function that will compute a total of the sale order lines
   4. Reading the countries info (code and name)

That's great because if you run this code on 1000 sales orders, you have the guarantee to only have 4 SQL queries.

Notes:

    * IDS is the list of the 10 ID's: [12,15,18,34, ...,99]
    * The arguments of a function are always the same:

          - cr: the cursor database (from psycopg)
          - uid: the user id (for security checks)
    * If you run this code on 5000 sales orders, you may have 8 SQL queries because as SQL queries are not allowed to take too much memory, it may have to do two separate readings.


Complex example
+++++++++++++++

Here is a complete example, from the OpenERP official distribution, of the function that does bill of material explosion and computation of associated routings:

.. code-block:: python

    class mrp_bom(osv.osv):
        ...
        def _bom_find(self, cr, uid, product_id, product_uom, properties=[]):
            bom_result = False
            # Why searching on BoM without parent ?
            cr.execute('select id from mrp_bom where product_id=%d and bom_id is null
                          order by sequence', (product_id,))
            ids = map(lambda x: x[0], cr.fetchall())
            max_prop = 0
            result = False
            for bom in self.pool.get('mrp.bom').browse(cr, uid, ids):
                prop = 0
                for prop_id in bom.property_ids:
                    if prop_id.id in properties:
                        prop+=1
                if (prop>max_prop) or ((max_prop==0) and not result):
                    result = bom.id
                    max_prop = prop
            return result

            def _bom_explode(self, cr, uid, bom, factor, properties, addthis=False, level=10):
                factor = factor / (bom.product_efficiency or 1.0)
                factor = rounding(factor, bom.product_rounding)
                if factor<bom.product_rounding:
                    factor = bom.product_rounding
                result = []
                result2 = []
                phantom = False
                if bom.type=='phantom' and not bom.bom_lines:
                    newbom = self._bom_find(cr, uid, bom.product_id.id,
                                            bom.product_uom.id, properties)
                    if newbom:
                        res = self._bom_explode(cr, uid, self.browse(cr, uid, [newbom])[0],
                              factor*bom.product_qty, properties, addthis=True, level=level+10)
                        result = result + res[0]
                        result2 = result2 + res[1]
                        phantom = True
                    else:
                        phantom = False
                if not phantom:
                    if addthis and not bom.bom_lines:
                        result.append(
                        {
                            'name': bom.product_id.name,
                            'product_id': bom.product_id.id,
                            'product_qty': bom.product_qty * factor,
                            'product_uom': bom.product_uom.id,
                            'product_uos_qty': bom.product_uos and 
                                               bom.product_uos_qty * factor or False,
                            'product_uos': bom.product_uos and bom.product_uos.id or False,
                        })
                    if bom.routing_id:
                        for wc_use in bom.routing_id.workcenter_lines:
                            wc = wc_use.workcenter_id
                            d, m = divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
                            mult = (d + (m and 1.0 or 0.0))
                            cycle = mult * wc_use.cycle_nbr
                            result2.append({
                                'name': bom.routing_id.name,
                                'workcenter_id': wc.id,
                                'sequence': level+(wc_use.sequence or 0),
                                'cycle': cycle,
                                'hour': float(wc_use.hour_nbr*mult +
                                              (wc.time_start+wc.time_stop+cycle*wc.time_cycle) *
                                               (wc.time_efficiency or 1.0)),
                            })
                    for bom2 in bom.bom_lines:
                         res = self._bom_explode(cr, uid, bom2, factor, properties,
                                                     addthis=True, level=level+10)
                         result = result + res[0]
                         result2 = result2 + res[1]
                return result, result2


Technical architecture
======================

OpenERP is a `multitenant <http://en.wikipedia.org/wiki/Multitenancy>`_,
`three-tier architecture
<http://en.wikipedia.org/wiki/Multitier_architecture#Three-tier_architecture>`_.
The application tier itself is written as a core, multiple additional
modules can be installed to create a particular configuration of
OpenERP.

The core of OpenERP and its modules are written in `Python
<http://python.org/>`_. The functionality of a module is exposed through
XML-RPC (and/or NET-RPC depending on the server's configuration)[#]. Modules
typically make use of OpenERP's ORM to persist their data in a relational
database (PostgreSQL). Modules can insert data in the database during
installation by providing XML, CSV, or YML files.

.. figure:: images/client_server.png
   :scale: 85
   :align: center

.. [#] JSON-RPC is planned for OpenERP v6.1.

The OpenERP server
------------------

OpenERP provides an application server on which specific business applications
can be built. It is also a complete development framework, offering a range of
features to write those applications. The salient features are a flexible ORM,
a MVC architecture, extensible data models and views, different report engines,
all tied together in a coherent, network-accessible framework.

From a developer perspective, the server acts both as a library which brings
the above benefits while hiding the low-level, nitty-gritty details, and as a
simple way to install, configure and run the written applications.

Modules
-------

By itself, the OpenERP server is not very useful. For any enterprise, the value
of OpenERP lies in its different modules. It is the role of the modules to
implement any business needs. The server is only the necessary machinery to run
the modules. A lot of modules already exist. Any official OpenERP release
includes about 170 of them, and hundreds of modules are available through the
community. Examples of modules are Account, CRM, HR, Marketing, MRP, Sale, etc.

A module is usually composed of data models, together with some initial data,
views definitions (i.e. how data from specific data models should be displayed
to the user), wizards (specialized screens to help the user for specific
interactions), workflows definitions, and reports.

Clients
-------

Clients can communicate with an OpenERP server using XML-RPC. A custom, faster
protocol called NET-RPC is also provided but will shortly disappear, replaced
by JSON-RPC. XML-RPC, as JSON-RPC in the future, makes it possible to write
clients for OpenERP in a variety of programming languages. OpenERP S.A.
develops two different clients: a desktop client, written with the widely used
`GTK+ <http://www.gtk.org/>`_ graphical toolkit, and a web client that should
run in any modern web browser.

As the logic of OpenERP should entirely reside on the server, the client is
conceptually very simple; it issues a request to the server and display the result
(e.g. a list of customers) in different manners (as forms, lists, calendars,
...). Upon user actions, it will send modified data to the server.

Relational database server and ORM
----------------------------------

The data tier of OpenERP is provided by a PostgreSQL relational database. While
direct SQL queries can be executed from OpenERP modules, most database access
to the relational database is done through the `Object-Relational Mapping
<http://en.wikipedia.org/wiki/Object-relational_mapping>`_.

The ORM is one of the salient features mentioned above. The data models are
described in Python and OpenERP creates the underlying database tables. All the
benefits of RDBMS (unique constraints, relational integrity, efficient
querying, ...) are used when possible and completed by Python flexibility. For
instance, arbitrary constraints written in Python can be added to any model.
Different modular extensibility mechanisms are also afforded by OpenERP[#].

.. [#] It is important to understand the ORM responsibility before attempting to by-pass it and access directly the underlying database via raw SQL queries.  When using the ORM, OpenERP can make sure the data remains free of any corruption.  For instance, a module can react to data creation in a particular table. This reaction can only happen if the ORM is used to create that data.

Models
------

To define data models and otherwise pursue any work with the associated data,
OpenERP as many ORMs uses the concept of 'model'. A model is the authoritative
specification of how some data are structured, constrained, and manipulated. In
practice, a model is written as a Python class. The class encapsulates anything
there is to know about the model: the different fields composing the model,
default values to be used when creating new records, constraints, and so on. It
also holds the dynamic aspect of the data it controls: methods on the class can
be written to implement any business needs (for instance, what to do upon user
action, or upon workflow transitions).

There are two different models. One is simply called 'model', and the second is
called 'transient model'. The two models provide the same capabilities with a
single difference: transient models are automatically cleared from the
database (they can be cleaned when some limit on the number of records is
reached, or when they are untouched for some time).

To describe the data model per se, OpenERP offers a range of different kind of
fields. There are basic fields such as integer, or text fields. There are
relational fields to implement one-to-many, many-to-one, and many-to-many
relationships. There are so-called function fields, which are dynamically
computed and are not necessarily available in database, and more.

Access to data is controlled by OpenERP and configured by different mechanisms.
This ensures that different users can have read and/or write access to only the
relevant data. Access can be controlled with respect to user groups and rules
based on the value of the data themselves.

Modules
-------

OpenERP supports a modular approach both from a development perspective and a
deployment point of view. In essence, a module groups everything related to a
single concern in one meaningful entity. It is comprised of models, views,
workflows, and wizards.

Services and WSGI
-----------------

Everything in OpenERP, and models methods in particular, are exposed via the
network and a security layer. Access to the data model is in fact a 'service'
and it is possible to expose new services. For instance, a WebDAV service and a
FTP service are available.

While not mandatory, the services can make use of the `WSGI
<http://en.wikipedia.org/wiki/Web_Server_Gateway_Interface>`_ stack.
WSGI is a standard solution in the Python ecosystem to write HTTP servers,
applications, and middleware which can be used in a mix-and-match fashion.
By using WSGI, it is possible to run OpenERP in any WSGI-compliant server, but
also to use OpenERP to host a WSGI application.

A striking example of this possibility is the OpenERP Web project. OpenERP Web
is the server-side counter part to the web clients. It is OpenERP Web which
provides the web pages to the browser and manages web sessions. OpenERP Web is
a WSGI-compliant application. As such, it can be run as a stand-alone HTTP
server or embedded inside OpenERP.

XML-RPC, JSON-RPC
-----------------

The access to the models makes also use of the WSGI stack. This can be done
using the XML-RPC protocol, and JSON-RPC will be added soon.


Explanation of modules:

**Server - Base distribution**

We use a distributed communication mechanism inside the OpenERP server. Our engine supports most commonly distributed patterns: request/reply, publish/subscribe, monitoring, triggers/callback, ...

Different business objects can be in different computers or the same objects can be on multiple computers to perform load-balancing.

**Server - Object Relational Mapping (ORM)**

This layer provides additional object functionality on top of PostgreSQL:

    * Consistency: powerful validity checks,
    * Work with objects (methods, references, ...)
    * Row-level security (per user/group/role)
    * Complex actions on a group of resources
    * Inheritance 

**Server - Web-Services**

The web-service module offer a common interface for all web-services

    * SOAP
    * XML-RPC
    * NET-RPC 

Business objects can also be accessed via the distributed object mechanism. They can all be modified via the client interface with contextual views.

**Server - Workflow Engine**

Workflows are graphs represented by business objects that describe the dynamics of the company. Workflows are also used to track processes that evolve over time.

An example of workflow used in OpenERP:

A sales order generates an invoice and a shipping order

**Server - Report Engine**

Reports in OpenERP can be rendered in different ways:

    * Custom reports: those reports can be directly created via the client interface, no programming required. Those reports are represented by business objects (ir.report.custom)
    * High quality personalized reports using openreport: no programming required but you have to write 2 small XML files:

          - a template which indicates the data you plan to report
          - an XSL:RML stylesheet 
    * Hard coded reports
    * OpenOffice Writer templates 

Nearly all reports are produced in PDF.

**Server - Business Objects**

Almost everything is a business object in OpenERP, they describe all data of the program (workflows, invoices, users, customized reports, ...). Business objects are described using the ORM module. They are persistent and can have multiple views (described by the user or automatically calculated).

Business objects are structured in the /module directory.

**Client - Wizards**

Wizards are graphs of actions/windows that the user can perform during a session.

**Client - Widgets**

Widgets are probably, although the origin of the term seems to be very difficult to trace, "WIndow gaDGETS" in the IT world, which mean they are gadgets before anything, which implement elementary features through a portable visual tool.

All common widgets are supported:

    * entries
    * textboxes
    * floating point numbers
    * dates (with calendar)
    * checkboxes
    * ... 

And also all special widgets:

    * buttons that call actions
    * references widgets

          - one2one

          - many2one

          - many2many

          - one2many in list

          - ... 

Widget have different appearances in different views. For example, the date widget in the search dialog represents two normal dates for a range of date (from...to...).

Some widgets may have different representations depending on the context. For example, the one2many widget can be represented as a form with multiple pages or a multi-columns list.

Events on the widgets module are processed with a callback mechanism. A callback mechanism is a process whereby an element defines the type of events he can handle and which methods should be called when this event is triggered. Once the event is triggered, the system knows that the event is bound to a specific method, and calls that method back. Hence callback. 


Module Integrations
===================

The are many different modules available for OpenERP and suited for different business models. Nearly all of these are optional (except ModulesAdminBase), making it easy to customize OpenERP to serve specific business needs. All the modules are in a directory named addons/ on the server. You simply need to copy or delete a module directory in order to either install or delete the module on the OpenERP platform.

Some modules depend on other modules. See the file addons/module/__openerp__.py for more information on the dependencies.

Here is an example of __openerp__.py:

.. code-block:: python

	{
	    "name" : "Open TERP Accounting",
	    "version" : "1.0",
	    "author" : "Bob Gates - Not So Tiny",
	    "website" : "http://www.openerp.com/",
	    "category" : "Generic Modules/Others",
	    "depends" : ["base"],
	    "description" : """A
	    Multiline
	    Description
	    """,
	    "init_xml" : ["account_workflow.xml", "account_data.xml", "account_demo.xml"],
	    "demo_xml" : ["account_demo.xml"],
	    "update_xml" : ["account_view.xml", "account_report.xml", "account_wizard.xml"],
	    "active": False,
	    "installable": True
	}

When initializing a module, the files in the init_xml list are evaluated in turn and then the files in the update_xml list are evaluated. When updating a module, only the files from the **update_xml** list are evaluated. 


Inheritance
===========

Traditional Inheritance
-----------------------

Introduction
++++++++++++

Objects may be inherited in some custom or specific modules. It is better to inherit an object to add/modify some fields.

It is done with::

        _inherit='object.name'
        
Extension of an object
++++++++++++++++++++++

There are two possible ways to do this kind of inheritance. Both ways result in a new class of data, which holds parent fields and behaviour as well as additional fields and behaviour, but they differ in heavy programatical consequences. 

While Example 1 creates a new subclass "custom_material" that may be "seen" or "used" by any view or tree which handles "network.material", this will not be the case for Example 2. 

This is due to the table (other.material) the new subclass is operating on, which will never be recognized by previous "network.material" views or trees.

Example 1::

        class custom_material(osv.osv):
	        _name = 'network.material'
	        _inherit = 'network.material'
	        _columns = {
		        'manuf_warranty': fields.boolean('Manufacturer warranty?'),
	        }
	        _defaults = {
		        'manuf_warranty': lambda *a: False,
               }
        custom_material()

.. tip:: Notice
        
        _name == _inherit

In this example, the 'custom_material' will add a new field 'manuf_warranty' to the object 'network.material'. New instances of this class will be visible by views or trees operating on the superclasses table 'network.material'.

This inheritancy is usually called "class inheritance" in Object oriented design. The child inherits data (fields) and behavior (functions) of his parent.


Example 2::

        class other_material(osv.osv):
	        _name = 'other.material'
	        _inherit = 'network.material'
	        _columns = {
		        'manuf_warranty': fields.boolean('Manufacturer warranty?'),
	        }
	        _defaults = {
		        'manuf_warranty': lambda *a: False,
               }
        other_material()

.. tip:: Notice

        _name != _inherit

In this example, the 'other_material' will hold all fields specified by 'network.material' and it will additionally hold a new field 'manuf_warranty'. All those fields will be part of the table 'other.material'. New instances of this class will therefore never been seen by views or trees operating on the superclasses table 'network.material'.

This type of inheritancy is known as "inheritance by prototyping" (e.g. Javascript), because the newly created subclass "copies" all fields from the specified superclass (prototype). The child inherits data (fields) and behavior (functions) of his parent. 

Inheritance by Delegation
-------------------------

 **Syntax :**::

	 class tiny_object(osv.osv)
	     _name = 'tiny.object'
	     _table = 'tiny_object'
	     _inherits = { 'tiny.object_a' : 'name_col_a', 'tiny.object_b' : 'name_col_b',
                        ..., 'tiny.object_n' : 'name_col_n' }
	     (...)    


The object 'tiny.object' inherits from all the columns and all the methods from the n objects 'tiny.object_a', ..., 'tiny.object_n'.

To inherit from multiple tables, the technique consists in adding one column to the table tiny_object per inherited object. This column will store a foreign key (an id from another table). The values *'name_col_a' 'name_col_b' ... 'name_col_n'* are of type string and determine the title of the columns in which the foreign keys from 'tiny.object_a', ..., 'tiny.object_n' are stored.

This inheritance mechanism is usually called " *instance inheritance* "  or  " *value inheritance* ". A resource (instance) has the VALUES of its parents. 
