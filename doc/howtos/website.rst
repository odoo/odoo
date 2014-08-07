==================
Building a website
==================

.. warning::

    * This guide assumes `basic knowledge of Python
      <http://docs.python.org/2/tutorial/>`_
    * This guide assumes an installed Odoo
    * For production deployment, see the dedicated guides
      *deploying with Gunicorn* and *deploying with mod_wsgi*

Creating a basic module
=======================

In Odoo, tasks are performed by creating modules.

Modules customize the behavior of an Odoo installation, either by adding new
behaviors or by altering existing ones (including behaviors added by other
modules).

First let's create a *module directory* which will contain a single module in
our case but may store multiple related (a project's) or not really related
(a company's) modules:

.. code-block:: console

    $ mkdir my-modules

then let's create the module's own directory:

.. code-block:: console

    $ mkdir my-modules/academy

An Odoo module is a valid `Python package
<http://docs.python.org/2/tutorial/modules.html#packages>`_ so it needs an
``__init__.py`` file:

.. code-block:: console

    $ touch my-modules/academy/__init__.py

Finally the mark of an Odoo module is the
:ref:`manifest file <core/module/manifest>`, a Python dictionary describing
various module metadata. Here is a minimal form::

    {
        # The human-readable name of your module, displayed in the interface
        'name': "Academy",
        # A more extensive description
        'description': """
        """,
        # Which modules must be installed for this one to work
        'depends': ['base'],
    }

which should go into :file:`my-modules/academy/__openerp__.py`

A demonstration module
======================

We have a "complete" module ready for installation.

Although it does absolutely nothing yet we can install it.

Let's create a new Postgres_ database:

    .. code-block:: console

        $ createdb academy

then install our new module into it:

    .. code-block:: console

        $ ./odoo.py --addons-path addons,my-modules -d academy -i academy

:option:`--addons-path <odoo.py --addons-path>`
    the (comma-separated) paths to *addons directories*. If only built-in
    modules are used, can be ommitted entirely.
:option:`-d <odoo.py -d>`
    the name of the Postgres_ database to install or update modules in
:option:`-i <odoo.py -i>`
    A module to install before running the server itself. All of a module's
    dependencies are installed before the module itself.

.. seealso::

    * In a production development setting, modules should generally be created
      using :ref:`Odoo's scaffolding <core/cmdline/scaffold>` rather than by
      hand

To the browser
==============

:ref:`Controllers <web/http/controllers>` interpret browser requests and send
data back.

Add a simple controller in a new :file:`my-modules/academy/controllers.py`::

    # -*- coding: utf-8 -*-
    from openerp import http

    class Academy(http.Controller):
        @http.route('/academy/', auth='public')
        def index(self):
            return "Hello, world!"

Then import that file in :file:`my-modules/academy/__init__.py`::

    from . import controllers

Shut down your server (:kbd:`^C`) then just restart it:

.. code-block:: console

    $ ./odoo.py --addons-path addons,my-modules

and open a page to http://localhost:8069/academy/, you should see your "page"
appear:

.. figure:: website/helloworld.png

Templates
=========

Generating HTML in Python isn't fun.

The usual solution is templates_, pseudo-documents with placeholders and
display logic. Odoo allows any Python templating system, but provides its
own :ref:`QWeb <web/qweb>` templating system which integrates with other Odoo
features. QWeb is an XML template engine, let's create an XML file for our
first template :file:`my-modules/academy/templates.xml`

.. code-block:: xml

    <openerp><data>
      <template id="index">
        <title>Academy</title>
        <t t-foreach="teachers" t-as="teacher">
            <p><t t-esc="teacher"/></p>
        </t>
      </template>
    </data></openerp>

then register the template in :file:`my-modules/academy/__openerp__.py`:

.. code-block:: python
    :emphasize-lines: 9

    {
        # The human-readable name of your module, displayed in the interface
        'name': "Academy",
        # A more extensive description
        'description': """
        """,
        # Which modules must be installed for this one to work
        'depends': ['base'],
        'data': ['templates.xml'],
    }

and change the controller to use our new template instead of directly
returning a string:

.. code-block:: python
    :emphasize-lines: 6-

    from openerp import http

    class Academy(http.Controller):
        @http.route('/academy/', auth='public')
        def index(self):
            return http.request.render('academy.index', {
                'teachers': ["Diana Padilla", "Jody Caroll", "Lester Vaughn"],
            })

finally restart Odoo while :option:`updating the module <odoo.py -u>` so
Odoo updates the manifest and install the template file:

.. code-block:: console

    $ odoo.py --addons-path addons,my-modules -d academy -u academy

Going to http://localhost:8069/academy/ should now result in:

.. image:: website/basic-list.png

Storing data in Odoo
====================

:ref:`Odoo models <core/orm/model>` map to database tables.

In the previous section we just displayed a list of string entered statically
in the Python code. This doesn't allow modifications and persistent storage
thereof, so we're now going to move our data to the database.

Defining the data model
-----------------------

The first step is to define an Odoo model by creating
:file:`my-modules/academy/models.py`::

    from openerp import fields
    from openerp import models

    class Teachers(models.Model):
        _name = 'academy.teachers'

        name = fields.Char()

to import it from :file:`my-modules/academy/__init__.py`::

    from . import controllers
    from . import models

and to set up basic :ref:`access control <core/security/acl>` for the model by
defining :file:`my-modules/academy/ir.model.access.csv` and adding it to the
manifest:

.. code-block:: text

    id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
    access_academy_teachers,access_academy_teachers,model_academy_teachers,,1,0,0,0

.. code-block:: python
    :emphasize-lines: 11

    {
        # The human-readable name of your module, displayed in the interface
        'name': "Academy",
        # A more extensive description
        'description': """
        """,
        # Which modules must be installed for this one to work
        'depends': ['base'],
        'data': [
            'templates.xml',
            'ir.model.access.csv',
        ],
    }

this simply gives read access (``perm_read``) to all users (``group_id:id``
left empty).

.. warning::

    the administrator user bypasses access control, he has access to all
    models even if not given access to them

Demonstration data
------------------

The second step is to add some demonstration data to the system so it's
possible to test eat easily. This is done by adding a ``demo``
:ref:`data file <core/data>` to the manifest:

.. code-block:: python
    :emphasize-lines: 13

    {
        # The human-readable name of your module, displayed in the interface
        'name': "Academy",
        # A more extensive description
        'description': """
        """,
        # Which modules must be installed for this one to work
        'depends': ['base'],
        'data': [
            'templates.xml',
            'ir.model.access.csv',
        ],
        'demo': ['demo.xml'],
    }

.. code-block:: xml

    <openerp><data>
      <record id="padilla" model="academy.teachers">
        <field name="name">Diana Padilla</field>
      </record>
      <record id="carroll" model="academy.teachers">
        <field name="name">Jody Carroll</field>
      </record>
      <record id="vaughn" model="academy.teachers">
        <field name="name">Lester Vaughn</field>
      </record>
    </data></openerp>

.. tip::

    :ref:`Data files <core/data>` can be used for demo and non-demo data.
    Demo data are only loaded in "demo mode" and can be used for flow testing
    and demonstration, non-demo data are always loaded and used as initial
    system setup.

    In this case we're using demo data because an actual user of the system
    would want to input or import their own teachers list, so this list is
    only for testing.

Accessing the data
------------------

The last step is to alter model and template to use our brand new data.

Fetch the records from the database instead of having a static list:

.. code-block:: python
    :emphasize-lines: 6-

    from openerp import http

    class Academy(http.Controller):
        @http.route('/academy/', auth='public')
        def index(self):
            Teachers = http.request.env['academy.teachers']
            return http.request.render('academy.index', {
                'teachers': Teachers.search([]),
            })

and because :meth:`~Model.search` returns a set of records (matching the
filter, in this case "all records") alter the template to print each
teacher's ``name``:

.. code-block:: xml
    :emphasize-lines: 5

    <openerp><data>
      <template id="index">
        <title>Academy</title>
        <t t-foreach="teachers" t-as="teacher">
          <p><t t-esc="teacher.id"/> <t t-esc="teacher.name"/></p>
        </t>
      </template>
    </data></openerp>

Restart the server while updating the module (in order to update the manifest
and templates and load the demo file):

.. code-block:: console

    $ ./odoo.py --addons-path addons,my-modules -d academy -u academy

then navigate to http://localhost:8069/academy/. The page should look
little different: names should simply be prefixed by a number (the database
``id`` of the teacher).

Website support
===============

Odoo bundles a module dedicated to building websites.

So far we've used controllers fairly directly, but Odoo 8 added deeper
integration and a few other services (e.g. default styling, theming) via the
``website`` module.

First, add ``website`` as a dependency to ``academy``:

.. code-block:: python
    :emphasize-lines: 8

    {
        # The human-readable name of your module, displayed in the interface
        'name': "Academy",
        # A more extensive description
        'description': """
        """,
        # Which modules must be installed for this one to work
        'depends': ['website'],
        'data': [
            'templates.xml',
            'ir.model.access.csv',
        ],
        'demo': ['demo.xml'],
    }

then the ``website`` flag on the controller:

.. code-block:: python
    :emphasize-lines: 4

    from openerp import http

    class Academy(http.Controller):
        @http.route('/academy/', auth='public', website=True)
        def index(self):
            Teachers = http.request.env['academy.teachers']
            return http.request.render('academy.index', {
                'teachers': Teachers.search([]),
            })

.. TODO: website support link

this sets up a few new variables on :ref:`the request object
<web/http/request>` and allows using the website layout in our template:

.. code-block:: xml
    :emphasize-lines: 3-6,10-12

    <openerp><data>
      <template id="index">
        <t t-call="website.layout">
          <t t-set="title">Academy</t>
          <div class="oe_structure">
            <div class="container">
              <t t-foreach="teachers" t-as="teacher">
                <p><t t-esc="teacher.id"/> <t t-esc="teacher.name"/></p>
              </t>
            </div>
          </div>
        </t>
      </template>
    </data></openerp>

after restarting the server while updating the module (in order to update the
manifest and template):

.. code-block:: console

    $ ./odoo.py --addons-path addons,my-modules -d academy -u academy

accessing http://localhost:8069/academy/ should yield a nicer looking page
with branding and a number of built-in page elements (top-level menu,
footer, …)

.. image:: website/layout.png

.. _templates: http://en.wikipedia.org/wiki/Web_template
.. _postgres:
.. _postgresql:
    http://www.postgresql.org
