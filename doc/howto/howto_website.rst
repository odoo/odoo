===================================
Howto: build a website with OpenERP
===================================

.. queue:: howto_website/series

.. warning::

   This guide assumes `basic knowledge of python
   <http://docs.python.org/2/tutorial/>`_.

   This guide assumes :ref:`an OpenERP installed and ready for
   development <getting_started_installation_source-link>`.

   For production deployment, see the dedicated guides
   :ref:`using-gunicorn` and :ref:`using-mod-wsgi`.

Minimal website module
======================

Hello, world!
-------------

In OpenERP, doing things takes the form of creating modules, and these
modules customize the behavior of the OpenERP installation. The first
step is thus to create a module:

.. todo:: code generator in oe?

    * Create empty module (mandatory name, category)
    * Create controller (parent class?)
    * Create model (concrete/abstract? Inherit?)
    * Add field?

* Create a new folder called :file:`academy` in a module directory,
  inside it create an empty file called :file:`__openerp__.py` with
  the following content:

  .. patch::

* Create a second file :file:`controllers.py`. This is where the code
  interacting directly with your web browser will live. For starters,
  just include the following in it:

  .. patch::

* Finally, create a third file :file:`__init__.py` containing just:

  .. patch::

  This makes :file:`controllers.py` "visible" to openerp (by running
  the code it holds).

.. todo::

   * instructions for start & install
   * db handling
     - if existing db, automatically selected
     - if no existing db, nodb -> login -> login of first db
     - dbfilter

Now start your OpenERP server and install your module in it, open a
web browser and navigate to http://localhost:8069. A page should
appear with just the words "Hello, world!" on it.

The default response type is HTML (although we only sent some text,
browsers are pretty good at finding ways to turn stuff into things
they can display). Let's prettify things a bit: instead of returning
just a bit of text, we can return a page, and use a tool/library like
bootstrap_ to get a nicer rendering than the default.

Change the string returned by the ``index`` method to get a more page-ish
output:

.. patch::

.. note::

   this example requires internet access at all time, as we're
   accessing a :abbr:`CDN (Content Delivery Network, large distributed
   networks hosting static files and trying to provide
   high-performance and high-availability of these files)`-hosted
   file.

Data input: URL and query
-------------------------

Being able to build a static page in code is nice, but makes for limited
usefulness (you could do that with static files in the first place, after all).

But you can also create controllers which use data provided in the access URL,
for instance so you have a single controller generating multiple pages. Any
query parameter (``?name=value``) is passed as a parameter to the controller
function, and is a string.

.. patch::

No validation is performed on query input values, it could be missing
altogether (if a user accesses ``/tas/`` directly) or it could be incorrectly
formatted. For this reason, query parameters are generally used to provide
"options" to a given page, and "required" data tends (when possible) to be
inserted directly in the URL.

This can be done by adding `converter patterns`_ to the URL in ``@http.route``:

.. patch::

These patterns can perform conversions directly (in this case the conversion
from a string URL section to a python integer) and will perform a some
validation (if the ``id`` is not a valid integer, the converter will return
a ``404 Not Found`` instead of generating a server error when the conversion
fails).

Templating: better experience in editing
----------------------------------------

So far we've created HTML output by munging together Python strings using
string concatenation and formatting. It works, but is not exactly fun to edit
(and somewhat unsafe to boot) as even advanced text editors have a hard time
understanding they're dealing with HTML embedded in Python code.

The usual solution is to use templates_, documents with placeholders which
can be "rendered" to produce final pages (or others). OpenERP lets you use
any Python templating system you want, but bundles its own
:doc:`QWeb </06_ir_qweb>` templating system which we'll later see offers
some useful features.

Let's move our 2 pseudo-templates from inline strings to actual templates:

.. patch::

.. FIXME how can I access a QWeb template from a auth=none controller?
         explicitly fetch a registry using request.session.db? That's a bit
         horrendous now innit?

.. todo:: reload/update of module?

.. _bootstrap: http://getbootstrap.com

.. _converter patterns: http://werkzeug.pocoo.org/docs/routing/#rule-format

.. _templates: http://en.wikipedia.org/wiki/Web_template
