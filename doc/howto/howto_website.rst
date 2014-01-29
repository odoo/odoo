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

Hello, world!
=============

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
=========================

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
========================================

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

.. todo:: how can I access a QWeb template from a auth=none
          controller? explicitly fetch a registry using
          request.session.db? That's a bit horrendous now innit?

This simplifies the controller code by moving data formatting out of
it, and generally makes it simpler for designers to edit the markup.

.. todo:: link to section about reusing/altering existing stuff,
          template overriding

OpenERP's Website support
=========================

OpenERP 8 is bundled with new modules dedicated specifically to
building websites (whether it be simply sets of pages or more complex
components such as blogs).

First, we'll install the ``website`` module: ``oe install website``.

.. todo:: is it possible that the page has *not* been replaced?

If you navigate to `your openerp`_, your basic page has now been
replaced by the generic empty index page. Because you are not
logged-in yet, the page has no content and just basic placeholders in
the header and footer. Click on the :guilabel:`Sign In` link, fill in
your credentials (``admin``/``admin`` by default), click
:guilabel:`Log in`.

You're now in OpenERP "proper", the backend/administrative
interface. We'll deal with it in :ref:`a latter section
<howto-website-administration>`, for how click on the
:menuselection:`Website` menu item, in the top-left of the browser
between :menuselection:`Messaging` and :menuselection:`Settings`.

You're back to your website, but are now an administrator and thus
have access to the advanced edition features of an OpenERP-build
website. Let's quickly run through them.

Mobile Preview
--------------

.. todo:: insert menu bar, mobile preview icon outlined

Because the OpenERP website system is built with bootstrap_, it is
easy to build "responsive" websites reacting to the size of the screen
and making best use of the available space.

The mobile preview does not give you the exact rendering of a
smartphone (if there's such a thing), but it goes some of the way and
lets you know if it's completely unusable without having to actually
switch to a smartphone and try to find out how to see your site with
it (especially during edition).

.. todo:: screenshot of page in desktop v mobile preview layout

Promote
-------

Lets you easily configure how your page should advertise its existence
to search engines: keywords matching the page's subject, nice titles
and descriptions for visitors finding the page via search engines.

.. todo:: screenshot promote

Content
-------

The content menu provides "top level" operations: manipulation of the
main menu (creation of new links, submenus, etc...) and creation of
high-level objects. At the moment only pages (they're the top-level
object for the ``website`` module), but installing the recruitment
module will add an entry to quick-create a new job offer, and the
events module one for a new event.

Customize
---------

The customize menu provides a number of loosely associated features,
broadly split in two sections:

Templates configuration
```````````````````````

Some templates provide alternative versions/structures. These
alternative version can be toggled from the template configuration
checkboxes. Two of these are bundled in ``website``, providing an
alternative blank footer to fill, and the other one replacing your
company's name by your company's logo in the navigation bar.

Theming
```````

As previously mentioned, OpenERP's website module uses bootstrap_ for
much of its basic styles and layout. This, in turns, allows using
existing bootstrap themes to alter the color scheme of your website.

:menuselection:`Customize --> Change Theme` opens a picker to a few
bundled Bootstrap themes, and lets you change the look of your site
quickly and on-the-fly.

.. todo:: creating or installing new boostrap themes?

HTML Editor
```````````

Opens a full-blown code editor on the current template, and lets you
easily edit templates in-place, either for a quick fix which is
simpler to perform in code yet from the page, or to try things out
before moving them to template files.

Help
----

Lists available tutorials, step-by-step lessons in using the website.
``website`` only provides :menuselection:`Help --> Insert a banner`
which shows some basic features of the website (snippets, edition,
mobile preview) while guiding the user through. Other modules can
provide additional tutorials for their advanced features.

Edit
----

Starts up the rich text editor, which lets you alter page text, add
links and images, change colors, etc…

Snippets
````````

:guilabel:`Insert Blocks` opens the snippets UI: pre-built layout
blocks which you can then fill with your own content (text, pictures,
…). Simply select a snippet and drag-and-drop it on your page. Guides
should appear when you start dragging a snippet, showing where the
snippet can be dropped.

Building your pages with OpenERP Website
========================================

As we've seen, your index page has "disappeared" and been replaced by
the one provided by ``website``. The page is not lost, but because
``website`` was installed after the ``academy`` module, its index
page takes over routing (two index pages exist, and one is picked
over the other).

To fix the issue, we can simply add ``website`` as a dependency to
``academy`` (that is, tell OpenERP that ``academy`` needs ``website``
to work right):

.. needs -u all to update metadata

.. patch::

.. todo:: website dispatch overrides blows up on auth=none (implicitly
          inherits website's index -> ``website_enabled`` -> tries to
          access ``request.registry['website']`` even though
          ``request.registry is None`` because ``auth='none'``)

          also template issues (see above) (enabled website to "fix")

This will cause ``academy``'s index page to overwrite ``website``'s.

Reload `your openerp`_. Your old index page is back.

However, none of the website edition tools are available. That is
because much of these tools are inserted and enabled by the website
layout template.  Let's use that layout instead of our own page
structure:

.. patch::

* ``website.layout`` is the main Website layout, it provides standard
  headers and footers as well as integration with various
  customization tools.

* there's quite a bit of complex markup, used as hooks for various
  features (e.g. snippets). Although technically not mandatory, some
  things will not work if they're not there.

* if you go in the HTML editor (:menuselection:`Customize --> HTML
  Editor`), you can see and edit your template

.. todo:: website template generator

If you try to add content to the TA pages using snippets, for instance
insert an :guilabel:`image-text` snippet to add a picture and a short
biography for a TA, you'll notice things don't work right: because
snippets are added in the template itself, they're content which is
the same across all pages using that template.

Thus snippets are mostly for generic content, when a given template is
only used for a single page, or to add content in HTML fields.

.. note::

    When creating a new page (e.g. via :menuselection:`Content --> New
    Page`), OpenERP will duplicate a "source" template, and create a
    new template for each page. As a result, it's safe to use
    dedicated-content snippets for "static" pages.

Time, then, to create more specific content.

Storing data in OpenERP
=======================

The conceptual storage model of OpenERP is simple: there are storage
tables, represented by OpenERP models, and inside these tables are
records. The first step, then, is to define a model.

We'll start by moving our teaching assistants in the database:

.. patch::

We've also altered the index method slightly, to retrieve our teaching
assistants from the database instead of storing them in a global list
in the module\ [#taprofile]_.

.. note:: :file:`ir.model.access.csv` is necessary to tell OpenERP that
          any user can *see* the teaching assistants: by default, only
          the administrator can see, edit, create or destroy objects.
          Here, we only change the ``read`` permission to allow any
          user to list and browse teaching assistants.

.. todo:: command/shortcut

Update the module, reload `your openerp`_… and the Teaching Assistants
list is empty since we haven't put any TA in the database.

Let's add them in data files:

.. patch::

Update the module again, reload `your openerp`_ and the TAs are
back. Click on a TA name, and you'll see an error message. Let's fix
the TA view now:

.. todo:: if ta template was modified in previous section, it's marked
          noupdate and updating the module will have no effect for no
          known reason. That's really quite annoying.

.. patch::

There are a few non-obvious things here, so let's go through them for
clarity:

* OpenERP provides a has a special `converter pattern`_, which knows
  how to retrieve OpenERP objects by identifier. Instead of an integer
  or other similar basic value, ``ta`` thus gets a full-blown
  ``academy.tas`` object, without having to retrieve it by hand (as is
  done in ``index``).

* However because the ``model()`` `converter pattern`_ takes an
  identifier, we have to alter the creation of ``ta``'s URL to include
  such an identifier, rather than an index in an array

* Finally, ``website.render()`` wants a dict as its rendering context,
  not an object, which is why we wrap our ``ta`` object into one.

We're still where we started this section though: if we add snippets
to or edit the text of a TA's page, these editions will be visible
across all TA pages since they'll be stored in the shared
``academy.ta`` template.

Not only that, but we can not even edit the TA's name, even though
it's not shared content.

Let's fix that first, instead of using the basic "display this
content" template tag ``t-esc``, we'll use one aware of OpenERP
objects and their fields:

.. patch::

Update the module, go into a TA page and activate the edition mode. If
you move your mouse over the TA's name, it is surrounded by a yellow
border, and you can edit its content. If you change the name of a TA
and save the page, the change is correctly stored in the TA's record,
the name is fixed when you go to the index page but other TAs remain
unaffected.

For the issue of customizing our TA profiles, we can expand our model
with a "freeform" HTML field:

.. patch::

Then, insert the new biographical content in the template using the
same object-aware template tag:

.. patch::

.. todo:: updating the ``name`` field from the RTE altered the
          template, which locked it...

Update the module, browse to a TA's page and open the edition mode
(using the :guilabel:`Edit` button in the window's top-right).  The
empty HTML field now displays a big placeholder image, if you drop
snippets in or write some content for one of the teaching assistants,
you will see that other TA profiles are unaffected.

A more complex model
--------------------

Up to now, we've been working with displaying and manipulating
objects representing teaching assistants. It's a basic and
simple concept, but not one which allows for much further
diving into interesting tools of OpenERP. Thus, let's add a
list of course lectures.

.. calendar model
.. demo data for events dates
.. access & formatting
.. sending & storing comments (?)

.. _howto-website-administration:

Administration and ERP Integration
==================================

.. create menu, action
   .. improve generated views
.. create list & form views for events

.. [#taprofile] the teaching assistants profile view ends up
                broken for now, but don't worry we'll get
                around to it

.. _bootstrap: http://getbootstrap.com

.. _converter pattern:
.. _converter patterns:
    http://werkzeug.pocoo.org/docs/routing/#rule-format

.. _templates: http://en.wikipedia.org/wiki/Web_template

.. _your openerp: http://localhost:8069/
