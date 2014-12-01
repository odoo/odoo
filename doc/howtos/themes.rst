.. highlight:: xml

===============
Building Themes
===============

Basic set up
============

Create a basic theme module with :command:`odoo.py scaffold` and the ``theme``
template: from the root Odoo folder, use

.. code-block:: console

    $ ./odoo.py scaffold -t theme "Dummy Theme" addons

this should create a new folder ``dummy_theme`` in the ``addons`` directory
with the structure:

.. code-block:: text

    addons/dummy_theme
    |-- __init__.py
    |-- __openerp__.py
    |-- static
    |   `-- style
    |       `-- custom.less
    `-- views
        |-- options.xml
        |-- pages.xml
        `-- snippets.xml

``static/styles`` contains your stylesheet(s), ``views`` contains the various
XML files describing the theme and theme features to Odoo.

Static Page
-----------

Creating a new template
'''''''''''''''''''''''

Create a new file :file:`odoo/addons/theme_dummy/views/pages.xml` and open it.

In odoo, a page means a new template. You don't need special skills, simply
copy paste the lines::

  <template id="website.hello" name="Homepage" page="True">
      <t t-call="website.layout">
          <div id="wrap" class="oe_structure oe_empty">
          </div>
      </t>
  </template>

Refresh the page and feel the hit.

Editing content on a page
'''''''''''''''''''''''''

You can now add your content! You should always use the Bootstrap structure as
below::

    <template id="website.hello" name="Homepage" page="True">
        <t t-call="website.layout">
            <div id="wrap" class="oe_structure oe_empty">
                <section>
                    <div class="container">
                        <div class="row">
                            <h1>This is Your Content</h1>
                            <p>Isn't amazing to edit everything inline?</p>
                            <hr/>
                        </div>
                    </div>
                </section>
            </div>
        </t>
    </template>

Adding new item in the menu
'''''''''''''''''''''''''''

Adding these few more lines will put the new page in your menu::

  <record id="hello_menu" model="website.menu">
      <field name="name">Hello</field>
      <field name="url">/page/hello</field>
      <field name="parent_id" ref="website.main_menu"/>
      <field name="sequence" type="int">20</field>
  </record>

Congrats! It's online! Now drag and drop some snippets on the page and let's
style!

Pimp Your Theme
---------------

Easy styling with less
''''''''''''''''''''''

In ``odoo/addons/theme_dummy/static`` create a new folder and name it
``style``. In the new folder ``odoo/addons/theme_dummy/static/style`` create a
file and name it ``custom.less``. Open ``custom.less`` in the text editor and
modify these lines as below:


.. code-block:: css

   .h1 {
       color: #215487;
   }
   .span {
       border: 2px solid black;
       background-color: #eee;
   }

Refresh the page and feel the hit.

Get the most of the dom
'''''''''''''''''''''''

Right-Click, inspect element. You can go deeper by styling the main layout
container. Here we try with the 'wrapwrap' id.

.. code-block:: css

   #wrapwrap {
        background-color: #222;
        width: 80%;
        margin: 0 auto;
   }

Easy layout with bootstrap
''''''''''''''''''''''''''

Open :file:`odoo/addons/theme_dummy/views/pages.xml` and add a new section::

  <section>
      <div class="container">
          <div class="row">
              <div class="alert alert-primary" role="alert">
                  <a href="#" class="alert-link">...</a>
              </div>
              <div class="col-md-6 bg-blue">
                  <h2>BLUE it!</h2>
              </div>
              <div class="col-md-6 bg-green">
                  <h2>GREEN THAT!</h2>
              </div>
          </div>
      </div>
  </section>

Refresh the page and check how it looks.

The background of the alert component is the default Bootstrap primary color.
The two other div your created have no custom styles applied yet.  Open
:file:`odoo/addons/theme_dummy/static/style/custom.less` and add these lines:

.. code-block:: css

        @brand-primary: #1abc9c;
        @color-blue: #3498db;
        @color-green: #2ecc71;

        .bg-blue { background: @color-blue; }
        .bg-green { background: @color-green; }

        .h2 { color: white; }

As you see, the default primary has changed and your new colors are shining!

Build Your First Snippet
------------------------

Setting up __openerp__.py
'''''''''''''''''''''''''

Open ``__openerp__.py`` and add a new line as below:

.. code-block:: python

   {
       'name': 'Dummy Theme',
       'description': 'Dummy Theme',
       'category': 'Website',
       'version': '1.0',
       'author': 'OpenERP SA',
       'depends': ['website'],
       'data': [
           'views/snippets.xml',
       ],
       'application': True,
   }

In ``odoo/addons/theme_learn/views`` create a new xml file, name it
``snippets.xml`` and open it in a text editor

Add your snippet in the menu
''''''''''''''''''''''''''''

Before typing your html code, you need to locate it in the WEBb. drop-down
menu.  In this case, we will add it at the end of the Structure section::

  <template id="snippets" inherit_id="website.snippets" name="Clean Theme snippets">
    <xpath expr="//div[@id='snippet_structure']" position="inside">
    </xpath>
  </template>

Now open a new div, do not give it any id or classes. It will contain your
snippet::

    <xpath expr="//div[@id='snippet_structure']" position="inside">
        <div>
        </div>
    </xpath>

A thumbnail is also needed to create a more attractive link in the menu. You
can use labels to focus on your themes snippets.  Simply add a new div with
the class ``oe_snippet_thumbnail`` and add your thumbnail image (100x79px)::

  <xpath expr="//div[@id='snippet_structure']" position="inside">
      <div>
          <div class="oe_snippet_thumbnail">
              <img class="oe_snippet_thumbnail_img" src="/theme_Dummy/static/img/blocks/block_title.png"/>
              <span class="oe_snippet_thumbnail_title">SNIP IT!</span>
          </div>
      </div>
  </xpath>

And voila! Your new snippet is now ready to use. Just drag and drop it on your
page to see it in action.

The snippet body
''''''''''''''''

A snippet has to be in a section with the class ``oe_snippet_body`` to work
correctly.  As Odoo use the Bootstrap framework, you have use containers and
rows to hold your content. Please refer the the Bootstrap documentation::

  <xpath expr="//div[@id='snippet_structure']" position="inside">
      <div>
          <div class="oe_snippet_thumbnail">
              <img class="oe_snippet_thumbnail_img" src="/theme_Dummy/static/img/blocks/block_title.png"/>
              <span class="oe_snippet_thumbnail_title">SNIP IT!</span>
          </div>

          <section class="oe_snippet_body fw_categories">
              <div class="container">
                  <div class="row">
                  </div>
              </div>
          </section>
      </div>
  </xpath>

Inside your fresh new row, add some bootstraped contents::

  <div class="col-md-12 text-center mt32 mb32">
      <h2>A great Title</h2>
      <h3 class="text-muted ">And a great subtitle too</h3>
      <p>Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. </p>
  </div>


Adding images to your snippet
'''''''''''''''''''''''''''''

You can easely add images in your snippets simply by setting up css
backgrounds images.

In ``odoo/addons/theme_dummy/static/`` create a new folder and name it
``img``. Put your images there, in sub-folders if needed.  Open
:file:`odoo/addons/theme_dummy/static/style/custom.less`, add these lines

.. code-block:: css

   @img-01: url("../img/img-boy.png");
   .dummy-boy { background-image: @img-01; }

   @img-02: url("../img/img-girl.png");
   .dummy-girl { background-image: @img-02; }

In :file:`odoo/addons/theme_dummy/views/pages.xml` change the correspondant
lines as below::

    <section>
        <div class="container">
            <div class="row dummy-bg">
                <div class="alert alert-primary" role="alert">
                <a href="#" class="alert-link">...</a>
                </div>
                <div class="col-md-6">
                <h2>BLUE it!</h2>
                    <div class="dummy-boy">
                    </div>
                </div>
                <div class="col-md-6">
                <h2>GREEN THAT!</h2>
                    <div class="dummy-girl">
                    </div>
                </div>
            </div>
        </div>
    </section>

Your new snippet is now ready to use. Just drag and drop it on your page to
see it in action.

Advanced Customization
======================

Defining Your Theme Options
---------------------------

Understanding XPath
'''''''''''''''''''

As your stylesheets are running on the whole website, giving more option to
your snippets and applying them independently will push your design
forward. In ``odoo/addons/theme_dummy/views/`` create a new file, name it
``options.xml`` and add these lines::

    <template id="gourman_website_options_pattern" inherit_id="website.snippet_options">
        <xpath expr="//div[@data-option='dummy_options']//ul" position="after">
        </xpath>
    </template>

Explain xpath
"""""""""""""

.. TODO:: syntax not correct (see website examples) 

Your option menu is now correctly set in the database, you can create an new dropdown menu.

Let's say yout want three options which will change the text color and the background.
In option.xml, add these lines inside the xpath::

      <li data-check_class="text-purple"><a>YOUR OPTION 1</a></li>
      <li class="dropdown-submenu">
          <a tabindex="-1" href="#">Your sub option</a>
          <ul class="dropdown-menu">
            <li data-select_class="bg-yellow"><a>YOUR OPTION 2</a></li>
            <li data-select_class="text-light-bg-dark"><a>YOUR OPTION 3</a></li>
            <li data-select_class=""><a>None</a></li>
          </ul>
      <li>

Simple less css options
'''''''''''''''''''''''

In order to see these options in action, you have to write some new css
classes. Open custom.css and add this new lines

.. code-block:: css

    @color-purple: #2ecc71;
    @color-yellow: #2ecc71;

    .text-purple { color: @color-purple; }
    .bg-yellow { background-color: @color-yellow;}
    .text-light-bg-dark { color: #eee; background-color: #222;}

Refresh the page. Select a snippet and click Customize. Choose one of your new
options apply it.

XPath & inherits
''''''''''''''''

You can also add images in your variables and use them on certain part of your
pages, snippets or any html element.

In :file:`odoo/addons/theme_dummy/static/style/custom.css` add these new lines

.. code:: css

    @bg-01: url("../img/background/bg-blur.jpg");

    .bg-01 {
        background-image: @bg-01;
    }

Now that you have set the background image, you can decide how and where the
user can use it, for example, on a simple div.

Open :file:`odoo/addons/theme_dummy/views/options.xml` and add this new xpath::

  <xpath expr="//div[@data-option='background-dummy']//ul" position="after">
      <ul class="dropdown-menu">
          <li data-value="bg-01">
              <a>Image 1</a>
          </li>
      </ul>
  </xpath>

Your option is ready to be applied but you want it to be shown only a certain
part of a snippet.

Open :file:`odoo/addons/theme_dummy/views/snippets.xml` and add a new snippet
with the method we learned previously::

    <xpath expr="//div[@id='snippet_structure']" position="inside">
        <div>
        <!-- Add a Thumbnail in the Website Builder drop-down menu -->
            <div class="oe_snippet_thumbnail">
                <img class="oe_snippet_thumbnail_img" src="/theme_Dummy/static/img/blocks/block_title.png"/>
                <span class="oe_snippet_thumbnail_title">Test OPTION</span>
            </div>
        <!-- Your Snippet content -->
            <section class="oe_snippet_body fw_categories">
                <div class="container">
                    <div class="row">
                        <div class="col-md-6 text-center mt32 mb32">
                            <h2>NO OPTION</h2>
                            <p>OFF</p>
                        </div>
                        <div class="col-md-6 text-center mt32 mb32 test-option">
                            <h2>OPTION</h2>
                            <p>This div has the 'test-option' class</p>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </xpath>

As you see, the second ``col-md`` has a class named ``test-option``.  We are
going to specify where this option can be turned on by adding the
``data-selector`` attribute.

Go back to your ``options.xml`` files, add these new lines::

  <xpath expr="//div[@data-option='background-dummy']" position="attributes">
      <attribute name="data-selector">test-option</attribute>
  </xpath>

Refresh your browser. You should now be able to add your image background on
the left div only.  The option is now available on each section but also on
the left div with the custom class.

The Image Database
------------------

Modifying the image database
''''''''''''''''''''''''''''

Odoo provides its own image library but you certainly want to adapt it to your
design.  Do not use the Media Manager uploading Tool to add image in your
theme. The images url's will be lost on reload!  Instead of uploading your
images, you can create your own library and disable the old ones.

In ``odoo/addons/theme_dummy/views/`` create a new file, name it
``images.xml`` and add these lines::

  <record id="image_bg_blue" model="ir.attachment">
      <field name="name">bg_blue.jpg</field>
      <field name="datas_fname">bg_blue.jpg</field>
      <field name="res_model">ir.ui.view</field>
      <field name="type">url</field>
      <field name="url">/theme_clean/static/img/library/bg/bg_blue.jpg</field>
  </record>

Your images is now available in your Media Manager.  And your Theme has a
total new look.

Theme Selector
==============

Set Up
------

Understanding theme variants
''''''''''''''''''''''''''''

Combining theme variants
''''''''''''''''''''''''
