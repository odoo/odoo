==========
Web Client
==========

.. highlight:: javascript

.. default-domain:: js

This guide is about creating modules for Odoo's web client. To create websites
with Odoo, see :doc:`website`.

.. warning::

    This guide assumes knowledge of:

    * Javascript basics and good practices
    * jQuery_
    * `Underscore.js`_


A Simple Module to Test the Web Framework
-----------------------------------------

It's not really possible to include the multiple JavaScript files that
constitute the Odoo web framework in a simple HTML file like we did in the
previous chapter. So we will create a simple module in Odoo that contains some
configuration to have a web component that will give us the possibility to
test the web framework.

To download the example module, use this bazaar command:

.. code-block:: sh

    bzr branch lp:~niv-openerp/+junk/oepetstore -r 1

Now you must add that folder to your the addons path when you launch Odoo
(``--addons-path`` parameter when you launch the ``odoo.py`` executable). Then
create a new database and install the new module ``oepetstore``.

Now let's see what files exist in that module:

.. code-block:: text

    oepetstore
    |-- __init__.py
    |-- __openerp__.py
    |-- petstore_data.xml
    |-- petstore.py
    |-- petstore.xml
    `-- static
        `-- src
            |-- css
            |   `-- petstore.css
            |-- js
            |   `-- petstore.js
            `-- xml
                `-- petstore.xml

This new module already contains some customization that should be easy to
understand if you already coded an Odoo module like a new table, some views,
menu items, etc... We'll come back to these elements later because they will
be useful to develop some example web module. Right now let's concentrate on
the essential: the files dedicated to web development.

Please note that all files to be used in the web part of an Odoo module must
always be placed in a ``static`` folder inside the module. This is mandatory
due to possible security issues. The fact we created the folders ``css``,
``js`` and ``xml`` is just a convention.

``oepetstore/static/css/petstore.css`` is our CSS file. It is empty right now
but we will add any CSS we need later.

``oepetstore/static/xml/petstore.xml`` is an XML file that will contain our
QWeb templates. Right now it is almost empty too. Those templates will be
explained later, in the part dedicated to QWeb templates.

``oepetstore/static/js/petstore.js`` is probably the most interesting part. It
contains the JavaScript of our application. Here is what it looks like right
now::

    openerp.oepetstore = function(instance) {
        var _t = instance.web._t,
            _lt = instance.web._lt;
        var QWeb = instance.web.qweb;

        instance.oepetstore = {};

        instance.oepetstore.HomePage = instance.web.Widget.extend({
            start: function() {
                console.log("pet store home page loaded");
            },
        });

        instance.web.client_actions.add('petstore.homepage', 'instance.oepetstore.HomePage');
    }

The multiple components of that file will explained progressively. Just know
that it doesn't do much things right now except display a blank page and print
a small message in the console.

Like Odoo's XML files containing views or data, these files must be indicated
in the ``__openerp__.py`` file. Here are the lines we added to explain to the
web client it has to load these files:

.. code-block:: python

    'js': ['static/src/js/*.js'],
    'css': ['static/src/css/*.css'],
    'qweb': ['static/src/xml/*.xml'],

These configuration parameters use wildcards, so we can add new files without
altering ``__openerp__.py``: they will be loaded by the web client as long as
they have the correct extension and are in the correct folder.

.. warning::

    In Odoo, all JavaScript files are, by default, concatenated in a single
    file. Then we apply an operation called the *minification* on that
    file. The minification will remove all comments, white spaces and
    line-breaks in the file. Finally, it is sent to the user's browser.

    That operation may seem complex, but it's a common procedure in big
    application like Odoo with a lot of JavaScript files. It allows to load
    the application a lot faster.

    It has the main drawback to make the application almost impossible to
    debug, which is very bad to develop. The solution to avoid this
    side-effect and still be able to debug is to append a small argument to
    the URL used to load Odoo: ``?debug``. So the URL will look like this:

    .. code-block:: text

        http://localhost:8069/?debug

    When you use that type of URL, the application will not perform all that
    concatenation-minification process on the JavaScript files. The
    application will take more time to load but you will be able to develop
    with decent debugging tools.

Odoo JavaScript Module
-------------------------

In the previous chapter, we explained that JavaScript do not have a correct
mechanism to namespace the variables declared in different JavaScript files
and we proposed a simple method called the Module pattern.

In Odoo's web framework there is an equivalent of that pattern which is
integrated with the rest of the framework.  Please note that **an Odoo web
module is a separate concept from an Odoo addon**. An addon is a folder with a
lot of files, a web module is not much more than a namespace for JavaScript.

The ``oepetstore/static/js/petstore.js`` already declare such a module::

    openerp.oepetstore = function(instance) {
        instance.oepetstore = {};

        instance.oepetstore.xxx = ...;
    }

In Odoo's web framework, you declare a JavaScript module by declaring a
function that you put in the global variable ``openerp``. The attribute you
set in that object must have the exact same name than your Odoo addon (this
addon is named ``oepetstore``, if I set ``openerp.petstore`` instead of
``openerp.oepetstore`` that will not work).

That function will be called when the web client decides to load your
addon. It is given a parameter named ``instance``, which represents the
current Odoo web client instance and contains all the data related to the
current session as well as the variables of all web modules.

The convention is to create a new namespace inside the ``instance`` object
which has the same name than you addon.  That's why we set an empty dictionary
in ``instance.oepetstore``. That dictionary is the namespace we will use to
declare all classes and variables used inside our module.

Classes
-------

JavaScript doesn't have a class mechanism like most object-oriented
programming languages. To be more exact, it provides language elements to make
object-oriented programming but you have to define by yourself how you choose
to do it.  Odoo's web framework provide tools to simplify this and let
programmers code in a similar way they would program in other languages like
Java. That class system is heavily inspired by John Resig's `Simple JavaScript
Inheritance <http://ejohn.org/blog/simple-javascript-inheritance/>`_.

To define a new class, you need to extend the :class:`openerp.web.Class`
class::

    instance.oepetstore.MyClass = instance.web.Class.extend({
        say_hello: function() {
            console.log("hello");
        },
    });

As you can see, you have to call :func:`instance.web.Class.extend` and give
it a dictionary. That dictionary will contain the methods and class attributes
of our new class. Here we simply put a method named ``say_hello()``. This
class can be instantiated and used like this::

    var my_object = new instance.oepetstore.MyClass();
    my_object.say_hello();
    // print "hello" in the console

You can access the attributes of a class inside a method using ``this``::

    instance.oepetstore.MyClass = instance.web.Class.extend({
        say_hello: function() {
            console.log("hello", this.name);
        },
    });

    var my_object = new instance.oepetstore.MyClass();
    my_object.name = "Nicolas";
    my_object.say_hello();
    // print "hello Nicolas" in the console

Classes can have a constructor, it is just a method named ``init()``. You can
pass parameters to the constructor like in most language::

    instance.oepetstore.MyClass = instance.web.Class.extend({
        init: function(name) {
            this.name = name;
        },
        say_hello: function() {
            console.log("hello", this.name);
        },
    });

    var my_object = new instance.oepetstore.MyClass("Nicolas");
    my_object.say_hello();
    // print "hello Nicolas" in the console

Classes can be inherited. To do so, use :func:`~openerp.web.Class.extend`
directly on your class just like you extended :class:`~openerp.web.Class`::

    instance.oepetstore.MySpanishClass = instance.oepetstore.MyClass.extend({
        say_hello: function() {
            console.log("hola", this.name);
        },
    });

    var my_object = new instance.oepetstore.MySpanishClass("Nicolas");
    my_object.say_hello();
    // print "hola Nicolas" in the console

When overriding a method using inheritance, you can use ``this._super()`` to
call the original method. ``this._super()`` is not a normal method of your
class, you can consider it's magic. Example::

    instance.oepetstore.MySpanishClass = instance.oepetstore.MyClass.extend({
        say_hello: function() {
            this._super();
            console.log("translation in Spanish: hola", this.name);
        },
    });

    var my_object = new instance.oepetstore.MySpanishClass("Nicolas");
    my_object.say_hello();
    // print "hello Nicolas \n translation in Spanish: hola Nicolas" in the console

Widgets Basics
--------------

In previous chapter we discovered jQuery and its DOM manipulation tools. It's
useful, but it's not sufficient to structure a real application. Graphical
user interface libraries like Qt, GTK or Windows Forms have classes to
represent visual components. In Odoo, we have the
:class:`~openerp.web.Widget` class. A widget is a generic component
dedicated to display content to the user.

Your First Widget
%%%%%%%%%%%%%%%%%

The start module you installed already contains a small widget::

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        start: function() {
            console.log("pet store home page loaded");
        },
    });

Here we create a simple widget by extending the :class:`openerp.web.Widget`
class. This one defines a method named :func:`~openerp.web.Widget.start` that
doesn't do anything really interesting right now.

You may also have noticed this line at the end of the file::

    instance.web.client_actions.add('petstore.homepage', 'instance.oepetstore.HomePage');

This last line registers our basic widget as a client action. Client actions
will be explained in the next part of this guide. For now, just remember that
this is what allows our widget to be displayed when we click on the
:menuselection:`Pet Store --> Pet Store --> Home Page` menu element.

Display Content
%%%%%%%%%%%%%%%

Widgets have a lot of methods and features, but let's start with the basics:
display some data inside the widget and how to instantiate a widget and
display it.

The ``HomePage`` widget already has a :func:`~openerp.web.Widget.start`
method. That method is automatically called after the widget has been
instantiated and it has received the order to display its content. We will use
it to display some content to the user.

To do so, we will also use the :attr:`~openerp.web.Widget.$el` attribute
that all widgets contain. That attribute is a jQuery object with a reference
to the HTML element that represents the root of our widget. A widget can
contain multiple HTML elements, but they must be contained inside one single
element. By default, all widgets have an empty root element which is a
``<div>`` HTML element.

A ``<div>`` element in HTML is usually invisible for the user if it does not
have any content. That explains why when the ``instance.oepetstore.HomePage``
widget is displayed you can't see anything: it simply doesn't have any
content. To show something, we will use some simple jQuery methods on that
object to add some HTML in our root element::

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        start: function() {
            this.$el.append("<div>Hello dear Odoo user!</div>");
        },
    });

That message will now appear when you go to the menu :menuselection:`Pet Store
--> Pet Store --> Home Page` (remember you need to refresh your web browser,
although there is not need to restart Odoo's server).

Now you should learn how to instantiate a widget and display its content. To
do so, we will create a new widget::

    instance.oepetstore.GreetingsWidget = instance.web.Widget.extend({
        start: function() {
            this.$el.append("<div>We are so happy to see you again in this menu!</div>");
        },
    });

Now we want to display the ``instance.oepetstore.GreetingsWidget`` inside the
home page. To do so we can use the :func:`~openerp.web.Widget.append`
method of ``Widget``::

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        start: function() {
            this.$el.append("<div>Hello dear Odoo user!</div>");
            var greeting = new instance.oepetstore.GreetingsWidget(this);
            greeting.appendTo(this.$el);
        },
    });

Here, the ``HomePage`` instantiate a ``GreetingsWidget`` (the first argument
of the constructor of ``GreetingsWidget`` will be explained in the next
part). Then it asks the ``GreetingsWidget`` to insert itself inside the DOM,
more precisely directly under the ``HomePage`` widget.

When the :func:`~openerp.web.Widget.appendTo` method is called, it asks the
widget to insert itself and to display its content. It's during the call to
:func:`~openerp.web.Widget.appentTo` that the
:func:`~openerp.web.Widget.start` method will be called.

To check the consequences of that code, let's use Chrome's DOM explorer. But
before that we will modify a little bit our widgets to have some classes on
some of our ``<div>`` elements so we can clearly see them in the explorer::

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        start: function() {
            this.$el.addClass("oe_petstore_homepage");
            ...
        },
    });
    instance.oepetstore.GreetingsWidget = instance.web.Widget.extend({
        start: function() {
            this.$el.addClass("oe_petstore_greetings");
            ...
        },
    });

The result will be this if you can find the correct DOM part in the DOM explorer:

.. code-block:: html

    <div class="oe_petstore_homepage">
        <div>Hello dear Odoo user!</div>
        <div class="oe_petstore_greetings">
            <div>We are so happy to see you again in this menu!</div>
        </div>
    </div>

Here we can clearly see the two ``<div>`` created implicitly by
:class:`~openerp.web.Widget`, because we added some classes on them. We can
also see the two divs containing messages we created using the jQuery methods
on ``$el``. Finally, note the ``<div class="oe_petstore_greetings">`` element
which represents the ``GreetingsWidget`` instance is *inside* the ``<div
class="oe_petstore_homepage">`` which represents the ``HomePage`` instance.

Widget Parents and Children
%%%%%%%%%%%%%%%%%%%%%%%%%%%

In the previous part, we instantiated a widget using this syntax::

    new instance.oepetstore.GreetingsWidget(this);

The first argument is ``this``, which in that case was a ``HomePage``
instance. This serves to indicate the Widget what other widget is his parent.

As we've seen, widgets are usually inserted in the DOM by another widget and
*inside* that other widget. This means most widgets are always a part of
another widget. We call the container the *parent*, and the contained widget
the *child*.

Due to multiple technical and conceptual reasons, it is necessary for a widget
to know who is his parent and who are its children. This is why we have that
first parameter in the constructor of all widgets.

:func:`~openerp.web.Widget.getParent` can be used to get the parent of a
widget::

    instance.oepetstore.GreetingsWidget = instance.web.Widget.extend({
        start: function() {
            console.log(this.getParent().$el );
            // will print "div.oe_petstore_homepage" in the console
        },
    });

:func:`~openerp.web.Widget.getChildren` can be used to get a list of its
children::

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        start: function() {
            var greeting = new instance.oepetstore.GreetingsWidget(this);
            greeting.appendTo(this.$el);
            console.log(this.getChildren()[0].$el);
            // will print "div.oe_petstore_greetings" in the console
        },
    });

You should also remember that, when you override the
:func:`~openerp.web.Widget.init` method of a widget you should always put the
parent as first parameter are pass it to ``this._super()``::

    instance.oepetstore.GreetingsWidget = instance.web.Widget.extend({
        init: function(parent, name) {
            this._super(parent);
            this.name = name;
        },
    });

Finally, if a widget does not logically have a parent (ie: because it's the
first widget you instantiate in an application), you can give null as a parent
instead::

    new instance.oepetstore.GreetingsWidget(null);

Destroying Widgets
%%%%%%%%%%%%%%%%%%

If you can display content to your users, you should also be able to erase
it. This can simply be done using the :func:`~openerp.web.Widget.destroy`
method:

    greeting.destroy();

When a widget is destroyed it will first call
:func:`~openerp.web.Widget.destroy` on all its children. Then it erases itself
from the DOM. The recursive call to destroy from parents to children is very
useful to clean properly complex structures of widgets and avoid memory leaks
that can easily appear in big JavaScript applications.

.. _howtos/web/qweb:

The QWeb Template Engine
------------------------

The previous part of the guide showed how to define widgets that are able to
display HTML to the user. The example ``GreetingsWidget`` used a syntax like
this::

    this.$el.append("<div>Hello dear Odoo user!</div>");

This technically allow us to display any HTML, even if it is very complex and
require to be generated by code. Although generating text using pure
JavaScript is not very nice, that would necessitate to copy-paste a lot of
HTML lines inside our JavaScript source file, add the ``"`` character at the
beginning and the end of each line, etc...

The problem is exactly the same in most programming languages needing to
generate HTML. That's why they typically use template engines. Example of
template engines are Velocity, JSP (Java), Mako, Jinja (Python), Smarty (PHP),
etc...

In Odoo we use a template engine developed specifically for Odoo's web
client. Its name is QWeb.

QWeb is an XML-based templating language, similar to `Genshi
<http://en.wikipedia.org/wiki/Genshi_(templating_language)>`_, `Thymeleaf
<http://en.wikipedia.org/wiki/Thymeleaf>`_ or `Facelets
<http://en.wikipedia.org/wiki/Facelets>`_ with a few peculiarities:

* It's implemented fully in JavaScript and rendered in the browser.
* Each template file (XML files) contains multiple templates, where template
  engine usually have a 1:1 mapping between template files and templates.
* It has special support in Odoo Web's :class:`~openerp.web.Widget`, though it
  can be used outside of Odoo's web client (and it's possible to use
  :class:`~openerp.web.Widget` without relying on QWeb).

The rationale behind using QWeb instead of existing javascript template
engines is that its extension mechanism is very similar to the Odoo view
inheritance mechanism. Like Odoo views a QWeb template is an XML tree and
therefore XPath or DOM manipulations are easy to perform on it.

Using QWeb inside a Widget
%%%%%%%%%%%%%%%%%%%%%%%%%%

First let's define a simple QWeb template in
``oepetstore/static/src/xml/petstore.xml`` file, the exact meaning will be
explained later:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>

    <templates xml:space="preserve">
        <t t-name="HomePageTemplate">
            <div style="background-color: red;">This is some simple HTML</div>
        </t>
    </templates>

Now let's modify the ``HomePage`` class. Remember that enigmatic line at the
beginning the the JavaScript source file?

::

    var QWeb = instance.web.qweb;

This is a line we recommend to copy-paste in all Odoo web modules. It is the
object giving access to all templates defined in template files that were
loaded by the web client. We can use the template we defined in our XML
template file like this::

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        start: function() {
            this.$el.append(QWeb.render("HomePageTemplate"));
        },
    });

Calling the ``QWeb.render()`` method asks to render the template identified by
the string passed as first parameter.

Another possibility commonly seen in Odoo code is to use ``Widget``'s
integration with QWeb::

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        template: "HomePageTemplate",
        start: function() {
            ...
        },
    });

When you put a ``template`` class attribute in a widget, the widget knows it
has to call ``QWeb.render()`` to render that template.

Please note there is a difference between those two syntaxes. When you use
``Widget``'s QWeb integration the ``QWeb.render()`` method is called *before*
the widget calls :func:`~openerp.web.Widget.start`. It will also take the root
element of the rendered template and put it as a replacement of the default
root element generated by the :class:`~openerp.web.Widget` class. This will
alter the behavior, so you should remember it.

QWeb Context
''''''''''''

Like with all template engines, QWeb templates can contain code able to
manipulate data that is given to the template.  To pass data to QWeb, use the
second argument to ``QWeb.render()``:

.. code-block:: xml

    <t t-name="HomePageTemplate">
        <div>Hello <t t-esc="name"/></div>
    </t>

::

    QWeb.render("HomePageTemplate", {name: "Nicolas"});

Result:

.. code-block:: html

    <div>Hello Nicolas</div>

When you use :class:`~openerp.web.Widget`'s integration you can not pass
additional data to the template. Instead the template will have a unique
``widget`` variable which is a reference to the current widget:

.. code-block:: xml

    <t t-name="HomePageTemplate">
        <div>Hello <t t-esc="widget.name"/></div>
    </t>

::

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        template: "HomePageTemplate",
        init: function(parent) {
            this._super(parent);
            this.name = "Nicolas";
        },
        start: function() {
        },
    });

Result:

.. code-block:: html

    <div>Hello Nicolas</div>

Template Declaration
''''''''''''''''''''

Now that we know everything about rendering templates we can try to understand
QWeb's syntax.

All QWeb directives use XML attributes beginning with the prefix ``t-``. To
declare new templates, we add a ``<t t-name="...">`` element into the XML
template file inside the root element ``<templates>``::

    <templates>
        <t t-name="HomePageTemplate">
            <div>This is some simple HTML</div>
        </t>
    </templates>

``t-name`` simply declares a template that can be called using
``QWeb.render()``.

Escaping
''''''''

To put some text in the HTML, use ``t-esc``:

.. code-block:: xml

    <t t-name="HomePageTemplate">
        <div>Hello <t t-esc="name"/></div>
    </t>


This will output the variable ``name`` and escape its content in case it
contains some characters that looks like HTML.  Please note the attribute
``t-esc`` can contain any type of JavaScript expression:

.. code-block:: xml

    <t t-name="HomePageTemplate">
        <div><t t-esc="3+5"/></div>
    </t>

Will render:

.. code-block:: html

    <div>8</div>

Outputting HTML
'''''''''''''''

If you know you have some HTML contained in a variable, use ``t-raw`` instead
of ``t-esc``:

.. code-block:: xml

    <t t-name="HomePageTemplate">
        <div><t t-raw="some_html"/></div>
    </t>

If
''

The basic alternative block of QWeb is ``t-if``:

.. code-block:: xml

    <t t-name="HomePageTemplate">
        <div>
            <t t-if="true == true">
                true is true
            </t>
            <t t-if="true == false">
                true is not true
            </t>
        </div>
    </t>

Although QWeb does not contains any structure for else.

Foreach
'''''''

To iterate on a list, use ``t-foreach`` and ``t-as``:

.. code-block:: xml

    <t t-name="HomePageTemplate">
        <div>
            <t t-foreach="names" t-as="name">
                <div>
                    Hello <t t-esc="name"/>
                </div>
            </t>
        </div>
    </t>

Setting the Value of an XML Attribute
'''''''''''''''''''''''''''''''''''''

QWeb has a special syntax to set the value of an attribute. You must use
``t-att-xxx`` and replace ``xxx`` with the name of the attribute:

.. code-block:: xml

    <t t-name="HomePageTemplate">
        <div>
            Input your name:
            <input type="text" t-att-value="defaultName"/>
        </div>
    </t>

To Learn More About QWeb
''''''''''''''''''''''''

For a QWeb reference, see :ref:`reference/qweb`.

Exercise
''''''''

.. exercise:: Usage of QWeb in Widgets

    Create a widget whose constructor contains two parameters aside from
    ``parent``: ``product_names`` and ``color``.  ``product_names`` is a list
    of strings, each one being a name of product. ``color`` is a string
    containing a color in CSS color format (ie: ``#000000`` for black). That
    widget should display the given product names one under the other, each
    one in a separate box with a background color with the value of ``color``
    and a border. You must use QWeb to render the HTML. This exercise will
    necessitate some CSS that you should put in
    ``oepetstore/static/src/css/petstore.css``. Display that widget in the
    ``HomePage`` widget with a list of five products and green as the
    background color for boxes.

    .. only:: solutions

        ::

            openerp.oepetstore = function(instance) {
                var _t = instance.web._t,
                    _lt = instance.web._lt;
                var QWeb = instance.web.qweb;

                instance.oepetstore = {};

                instance.oepetstore.HomePage = instance.web.Widget.extend({
                    start: function() {
                        var products = new instance.oepetstore.ProductsWidget(this, ["cpu", "mouse", "keyboard", "graphic card", "screen"], "#00FF00");
                        products.appendTo(this.$el);
                    },
                });

                instance.oepetstore.ProductsWidget = instance.web.Widget.extend({
                    template: "ProductsWidget",
                    init: function(parent, products, color) {
                        this._super(parent);
                        this.products = products;
                        this.color = color;
                    },
                });

                instance.web.client_actions.add('petstore.homepage', 'instance.oepetstore.HomePage');
            }

        .. code-block:: xml

            <?xml version="1.0" encoding="UTF-8"?>

            <templates xml:space="preserve">
                <t t-name="ProductsWidget">
                    <div>
                        <t t-foreach="widget.products" t-as="product">
                            <span class="oe_products_item" t-att-style="'background-color: ' + widget.color + ';'"><t t-esc="product"/></span><br/>
                        </t>
                    </div>
                </t>
            </templates>

        .. code-block:: css

            .oe_products_item {
                display: inline-block;
                padding: 3px;
                margin: 5px;
                border: 1px solid black;
                border-radius: 3px;
            }

        .. image:: web/qweb.*
           :align: center
           :width: 70%

Widget Events and Properties
----------------------------

Widgets still have more helper to learn. One of the more complex (and useful)
one is the event system. Events are also closely related to the widget
properties.

Events
%%%%%%

Widgets are able to fire events in a similar way most components in existing
graphical user interfaces libraries (Qt, GTK, Swing,...) handle
them. Example::

    instance.oepetstore.ConfirmWidget = instance.web.Widget.extend({
        start: function() {
            var self = this;
            this.$el.append("<div>Are you sure you want to perform this action?</div>" +
                "<button class='ok_button'>Ok</button>" +
                "<button class='cancel_button'>Cancel</button>");
            this.$el.find("button.ok_button").click(function() {
                self.trigger("user_choose", true);
            });
            this.$el.find("button.cancel_button").click(function() {
                self.trigger("user_choose", false);
            });
        },
    });

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        start: function() {
            var widget = new instance.oepetstore.ConfirmWidget(this);
            widget.on("user_choose", this, this.user_choose);
            widget.appendTo(this.$el);
        },
        user_choose: function(confirm) {
            if (confirm) {
                console.log("The user agreed to continue");
            } else {
                console.log("The user refused to continue");
            }
        },
    });

First, we will explain what this example is supposed to do. We create a
generic widget to ask the user if he really wants to do an action that could
have important consequences (a type widget heavily used in Windows). To do so,
we put two buttons in the widget. Then we bind jQuery events to know when the
user click these buttons.

.. note::

    It could be hard to understand this particular line::

        var self = this;

    Remember, in JavaScript the variable ``this`` is a variable that is passed
    implicitly to all functions. It allows us to know which is the object if
    function is used like a method. Each declared function has its own
    ``this``. So, when we declare a function inside a function, that new
    function will have its own ``this`` that could be different from the
    ``this`` of the parent function. If we want to remember the original
    object the simplest method is to store a reference in a variable. By
    convention in Odoo we very often name that variable ``self`` because it's
    the equivalent of ``this`` in Python.

Since our widget is supposed to be generic, it should not perform any precise
action by itself. So, we simply make it trigger and event named
``user_choose`` by using the :func:`~openerp.web.Widget.trigger` method.

:func:`~openerp.web.Widget.trigger` takes as first argument the name of the
event to trigger. Then it can takes any number of additional arguments. These
arguments will be passed to all the event listeners.

Then we modify the ``HomePage`` widget to instantiate a ``ConfirmWidget`` and
listen to its ``user_choose`` event by calling the
:func:`~openerp.web.Widget.on` method.

:func:`~openerp.web.Widget.on` allows to bind a function to be called when the
event identified by event_name is ``triggered``. The ``func`` argument is the
function to call and ``object`` is the object to which that function is
related if it is a method. The binded function will be called with the
additional arguments of :func:`~openerp.web.Widget.trigger` if it has
any. Example::

    start: function() {
        var widget = ...
        widget.on("my_event", this, this.my_event_triggered);
        widget.trigger("my_event", 1, 2, 3);
    },
    my_event_triggered: function(a, b, c) {
        console.log(a, b, c);
        // will print "1 2 3"
    }

Properties
%%%%%%%%%%

Properties are very similar to normal object attributes. They allow to set
data on an object but with an additional feature: it triggers events when a
property's value has changed::

    start: function() {
        this.widget = ...
        this.widget.on("change:name", this, this.name_changed);
        this.widget.set("name", "Nicolas");
    },
    name_changed: function() {
        console.log("The new value of the property 'name' is", this.widget.get("name"));
    }

:func:`~openerp.web.Widget.set` allows to set the value of property. If the
value changed (or it didn't had a value previously) the object will trigger a
``change:xxx`` where ``xxx`` is the name of the property.

:func:`~openerp.web.Widget.get` allows to retrieve the value of a property.

Exercise
%%%%%%%%

.. exercise:: Widget Properties and Events

    Create a widget ``ColorInputWidget`` that will display 3 ``<input
    type="text">``. Each of these ``<input>`` is dedicated to type a
    hexadecimal number from 00 to FF. When any of these ``<input>`` is
    modified by the user the widget must query the content of the three
    ``<input>``, concatenate their values to have a complete CSS color code
    (ie: ``#00FF00``) and put the result in a property named ``color``. Please
    note the jQuery ``change()`` event that you can bind on any HTML
    ``<input>`` element and the ``val()`` method that can query the current
    value of that ``<input>`` could be useful to you for this exercise.

    Then, modify the ``HomePage`` widget to instantiate ``ColorInputWidget``
    and display it. The ``HomePage`` widget should also display an empty
    rectangle. That rectangle must always, at any moment, have the same
    background color than the color in the ``color`` property of the
    ``ColorInputWidget`` instance.

    Use QWeb to generate all HTML.

    .. only:: solutions

        ::

            openerp.oepetstore = function(instance) {
                var _t = instance.web._t,
                    _lt = instance.web._lt;
                var QWeb = instance.web.qweb;

                instance.oepetstore = {};

                instance.oepetstore.ColorInputWidget = instance.web.Widget.extend({
                    template: "ColorInputWidget",
                    start: function() {
                        var self = this;
                        this.$el.find("input").change(function() {
                            self.input_changed();
                        });
                        self.input_changed();
                    },
                    input_changed: function() {
                        var color = "#";
                        color += this.$el.find(".oe_color_red").val();
                        color += this.$el.find(".oe_color_green").val();
                        color += this.$el.find(".oe_color_blue").val();
                        this.set("color", color);
                    },
                });

                instance.oepetstore.HomePage = instance.web.Widget.extend({
                    template: "HomePage",
                    start: function() {
                        this.colorInput = new instance.oepetstore.ColorInputWidget(this);
                        this.colorInput.on("change:color", this, this.color_changed);
                        this.colorInput.appendTo(this.$el);
                    },
                    color_changed: function() {
                        this.$el.find(".oe_color_div").css("background-color", this.colorInput.get("color"));
                    },
                });

                instance.web.client_actions.add('petstore.homepage', 'instance.oepetstore.HomePage');
            }

        .. code-block:: xml

            <?xml version="1.0" encoding="UTF-8"?>

            <templates xml:space="preserve">
                <t t-name="ColorInputWidget">
                    <div>
                        Red: <input type="text" class="oe_color_red" value="00"></input><br />
                        Green: <input type="text" class="oe_color_green" value="00"></input><br />
                        Blue: <input type="text" class="oe_color_blue" value="00"></input><br />
                    </div>
                </t>
                <t t-name="HomePage">
                    <div>
                        <div class="oe_color_div"></div>
                    </div>
                </t>
            </templates>

        .. code-block:: css

            .oe_color_div {
                width: 100px;
                height: 100px;
                margin: 10px;
            }

        .. note::

            jQuery's ``css()`` method allows setting a css property.

Widget Helpers
--------------

We've seen the basics of the :class:`~openerp.web.Widget` class, QWeb and the
events/properties system. There are still some more useful methods proposed by
this class.

``Widget``'s jQuery Selector
%%%%%%%%%%%%%%%%%%%%%%%%%%%%

It is very common to need to select a precise element inside a widget. In the
previous part of this guide we've seen a lot of uses of the ``find()`` method
of jQuery objects::

    this.$el.find("input.my_input")...

:class:`~openerp.web.Widget` provides a shorter syntax that does the same
thing with the :func:`~openerp.web.Widget.$` method::

    instance.oepetstore.MyWidget = instance.web.Widget.extend({
        start: function() {
            this.$("input.my_input")...
        },
    });

.. note::

    We strongly advise you against using directly the global jQuery function
    ``$()`` like we did in the previous chapter were we explained the jQuery
    library and jQuery selectors. That type of global selection is sufficient
    for simple applications but is not a good idea in real, big web
    applications. The reason is simple: when you create a new type of widget
    you never know how many times it will be instantiated. Since the ``$()``
    global function operates in *the whole HTML displayed in the browser*, if
    you instantiate a widget 2 times and use that function you will
    incorrectly select the content of another instance of your widget. That's
    why you must restrict the jQuery selections to HTML which is located
    *inside* your widget most of the time.

    Applying the same logic, you can also guess it is a very bad idea to try
    to use HTML ids in any widget. If the widget is instantiated 2 times you
    will have 2 different HTML element in the whole application that have the
    same
    id. And that is an error by itself. So you should stick to CSS classes to mark your HTML elements in all cases.

Easier DOM Events Binding
%%%%%%%%%%%%%%%%%%%%%%%%%

In the previous part, we had to bind a lot of HTML element events like
``click()`` or ``change()``. Now that we have the ``$()`` method to simplify
code a little, let's see how it would look like::

    instance.oepetstore.MyWidget = instance.web.Widget.extend({
        start: function() {
            var self = this;
            this.$(".my_button").click(function() {
                self.button_clicked();
            });
        },
        button_clicked: function() {
            ..
        },
    });

It's still a bit long to type. That's why there is an even more simple syntax
for that::

    instance.oepetstore.MyWidget = instance.web.Widget.extend({
        events: {
            "click .my_button": "button_clicked",
        },
        button_clicked: function() {
            ..
        }
    });

.. warning::

    It's important to differentiate the jQuery events that are triggered on
    DOM elements and events of the widgets. The ``event`` class attribute *is
    a helper to help binding jQuery events*, it has nothing to do with the
    widget events that can be binded using the ``on()`` method.

The ``event`` class attribute is a dictionary that allows to define jQuery
events with a shorter syntax.

The key is a string with 2 different parts separated with a space. The first
part is the name of the event, the second one is the jQuery selector. So the
key ``click .my_button`` will bind the event ``click`` on the elements
matching the selector ``my_button``.

The value is a string with the name of the method to call on the current
object.

Development Guidelines
%%%%%%%%%%%%%%%%%%%%%%

As explained in the prerequisites to read this guide, you should already know
HTML and CSS. But developing web applications in JavaScript or developing web
modules for Odoo require to be more strict than you will usually be when
simply creating static web pages with CSS to style them. So these guidelines
should be followed if you want to have manageable projects and avoid bugs or
common mistakes:

* Identifiers (``id`` attribute) should be avoided. In generic applications
  and modules, ``id`` limits the re-usability of components and tends to make
  code more brittle. Just about all the time, they can be replaced with
  nothing, with classes or with keeping a reference to a DOM node or a jQuery
  element around.

  .. note::

      If it is absolutely necessary to have an ``id`` (because a third-party
      library requires one and can't take a DOM element), it should be
      generated with ``_.uniqueId()``.

* Avoid predictable/common CSS class names. Class names such as "content" or
  "navigation" might match the desired meaning/semantics, but it is likely an
  other developer will have the same need, creating a naming conflict and
  unintended behavior. Generic class names should be prefixed with e.g. the
  name of the component they belong to (creating "informal" namespaces, much
  as in C or Objective-C).

* Global selectors should be avoided. Because a component may be used several
  times in a single page (an example in Odoo is dashboards), queries should be
  restricted to a given component's scope. Unfiltered selections such as
  ``$(selector)`` or ``document.querySelectorAll(selector)`` will generally
  lead to unintended or incorrect behavior.  Odoo Web's
  :class:`~openerp.web.Widget` has an attribute providing its DOM root
  (:attr:`~openerp.web.Widget.$el`), and a shortcut to select nodes directly
  (:func:`~openerp.web.Widget.$`).

* More generally, never assume your components own or controls anything beyond
  its own personal :attr:`~openerp.web.Widget.$el`

* html templating/rendering should use QWeb unless absolutely trivial.

* All interactive components (components displaying information to the screen
  or intercepting DOM events) must inherit from Widget and correctly implement
  and use its API and life cycle.

Modify Existent Widgets and Classes
-----------------------------------

The class system of the Odoo web framework allows direct modification of
existing classes using the :func:`~openerp.web.Widget.include` method of a
class::

    var TestClass = instance.web.Class.extend({
        testMethod: function() {
            return "hello";
        },
    });

    TestClass.include({
        testMethod: function() {
            return this._super() + " world";
        },
    });

    console.log(new TestClass().testMethod());
    // will print "hello world"

This system is similar to the inheritance mechanism, except it will directly
modify the class. You can call ``this._super()`` to call the original
implementation of the methods you are redefining. If the class already had
sub-classes, all calls to ``this._super()`` in sub-classes will call the new
implementations defined in the call to ``include()``. This will also work if
some instances of the class (or of any of its sub-classes) were created prior
to the call to :func:`~openerp.web.Widget.include`.

.. warning::

    Please note that, even if :func:`~openerp.web.Widget.include` can be a
    powerful tool, it's not considered a very good programming practice
    because it can easily create problems if used in a wrong way. So you
    should use it to modify the behavior of an existing component only when
    there are no other options, and try to limit its usages to the strict
    minimum.

Translations
------------

The process to translate text in Python and JavaScript code is very
similar. You could have noticed these lines at the beginning of the
``petstore.js`` file:

    var _t = instance.web._t,
        _lt = instance.web._lt;

These lines are simply used to import the translation functions in the current
JavaScript module. The correct to use them is this one::

    this.$el.text(_t("Hello dear user!"));

In Odoo, translations files are automatically generated by scanning the source
code. All piece of code that calls a certain function are detected and their
content is added to a translation file that will then be sent to the
translators. In Python, the function is ``_()``. In JavaScript the function is
:func:`~openerp.web._t` (and also :func:`~openerp.web._lt`).

If the source file as never been scanned and the translation files does not
contain any translation for the text given to ``_t()`` it will return the text
as-is. If there is a translation it will return it.

:func:`~openerp.web._lt` does almost the exact same thing but is a little bit
more complicated. It does not return a text but returns a function that will
return the text. It is reserved for very special cases::

    var text_func = _lt("Hello dear user!");
    this.$el.text(text_func());

To have more information about Odoo's translations, please take a look at the
reference documentation: https://doc.openerp.com/contribute/translations/ .

Communication with the Odoo Server
-------------------------------------

Now you should know everything you need to display any type of graphical user
interface with your Odoo modules.  Still, Odoo is a database-centric
application so it's still not very useful if you can't query data from the
database.

As a reminder, in Odoo you are not supposed to directly query data from the
PostgreSQL database, you will always use the build-in ORM (Object-Relational
Mapping) and more precisely the Odoo *models*.

Contacting Models
%%%%%%%%%%%%%%%%%

In the previous chapter we explained how to send HTTP requests to the web
server using the ``$.ajax()`` method and the JSON format. It is useful to know
how to make a JavaScript application communicate with its web server using
these tools, but it's still a little bit low-level to be used in a complex
application like Odoo.

When the web client contacts the Odoo server it has to pass additional data
like the necessary information to authenticate the current user. There is also
some more complexity due to Odoo models that need a higher-level communication
protocol to be used.

This is why you will not use directly ``$.ajax()`` to communicate with the
server. The web client framework provides classes to abstract that protocol.

To demonstrate this, the file ``petstore.py`` already contains a small model
with a sample method:

.. code-block:: python

    class message_of_the_day(osv.osv):
        _name = "message_of_the_day"

        def my_method(self, cr, uid, context=None):
            return {"hello": "world"}

        _columns = {
            'message': fields.text(string="Message"),
            'color': fields.char(string="Color", size=20),
        }

If you know Odoo models that code should be familiar to you. This model
declares a table named ``message_of_the_day`` with two fields. It also has a
method ``my_method()`` that doesn't do much except return a dictionary.

Here is a sample widget that calls ``my_method()`` and displays the result::

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        start: function() {
            var self = this;
            var model = new instance.web.Model("message_of_the_day");
            model.call("my_method", [], {context: new instance.web.CompoundContext()}).then(function(result) {
                self.$el.append("<div>Hello " + result["hello"] + "</div>");
                // will show "Hello world" to the user
            });
        },
    });

The class used to contact Odoo models is ``instance.web.Model``. When you
instantiate it, you must give as first argument to its constructor the name of
the model you want to contact in Odoo. (Here it is ``message_of_the_day``, the
model created for this example, but it could be any other model like
``res.partner``.)

:func:`~openerp.web.Model.call` is the method of :class:`~openerp.web.Model`
used to call any method of an Odoo server-side model. Here are its arguments:

* ``name`` is the name of the method to call on the model. Here it is the
  method named ``my_method``.
* ``args`` is a list of positional arguments to give to the method. The sample
  ``my_method()`` method does not contain any particular argument we want to
  give to it, so here is another example:

  .. code-block:: python

      def my_method2(self, cr, uid, a, b, c, context=None): ...

  .. code-block:: javascript

      model.call("my_method", [1, 2, 3], ...
      // with this a=1, b=2 and c=3

* ``kwargs`` is a list of named arguments to give to the method. In the
  example, we have one named argument which is a bit special:
  ``context``. It's given a value that may seem very strange right now: ``new
  instance.web.CompoundContext()``. The meaning of that argument will be
  explained later. Right now you should just know the ``kwargs`` argument
  allows to give arguments to the Python method by name instead of
  position. Example:

  .. code-block:: python

      def my_method2(self, cr, uid, a, b, c, context=None): ...

  .. code-block:: javascript

      model.call("my_method", [], {a: 1, b: 2, c: 3, ...
      // with this a=1, b=2 and c=3

.. note::

    If you take a look at the ``my_method()``'s declaration in Python, you can
    see it has two arguments named ``cr`` and ``uid``:

    .. code-block:: python

        def my_method(self, cr, uid, context=None):

    You could have noticed we do not give theses arguments to the server when
    we call that method from JavaScript. That is because theses arguments that
    have to be declared in all models' methods are never sent from the Odoo
    client.  These arguments are added implicitly by the Odoo server. The
    first one is an object called the *cursor* that allows communication with
    the database. The second one is the id of the currently logged in user.

:func:`~openerp.web.Widget.call` returns a deferred resolved with the value
returned by the model's method as first argument. If you don't know what
deferreds are, take a look at the previous chapter (the part about HTTP
requests in jQuery).

CompoundContext
%%%%%%%%%%%%%%%

In the previous part, we avoided to explain the strange ``context`` argument
in the call to our model's method:

.. code-block:: javascript

    model.call("my_method", [], {context: new instance.web.CompoundContext()})

In Odoo, models' methods should always have an argument named ``context``:

.. code-block:: python

    def my_method(self, cr, uid, context=None): ...

The context is like a "magic" argument that the web client will always give to
the server when calling a method. The context is a dictionary containing
multiple keys. One of the most important key is the language of the user, used
by the server to translate all the messages of the application. Another one is
the time zone of the user, used to compute correctly dates and times if Odoo
is used by people in different countries.

The ``argument`` is necessary in all methods, because if we forget it bad
things could happen (like the application not being translated
correctly). That's why, when you call a model's method, you should always give
it to that argument. The solution to achieve that is to use
:class:`openerp.web.CompoundContext`.

:class:`~openerp.web.CompoundContext` is a class used to pass the user's
context (with language, time zone, etc...) to the server as well as adding new
keys to the context (some models' methods use arbitrary keys added to the
context). It is created by giving to its constructor any number of
dictionaries or other :class:`~openerp.web.CompoundContext` instances. It will
merge all those contexts before sending them to the server.

.. code-block:: javascript

    model.call("my_method", [], {context: new instance.web.CompoundContext({'new_key': 'key_value'})})

.. code-block:: python

    def display_context(self, cr, uid, context=None):
        print context
        // will print: {'lang': 'en_US', 'new_key': 'key_value', 'tz': 'Europe/Brussels', 'uid': 1}

You can see the dictionary in the argument ``context`` contains some keys that
are related to the configuration of the current user in Odoo plus the
``new_key`` key that was added when instantiating
:class:`~openerp.web.CompoundContext`.

To resume, you should always add an instance of
:class:`~openerp.web.CompoundContext` in all calls to a model's method.

Queries
%%%%%%%

If you know Odoo module development, you should already know everything
necessary to communicate with models and make them do what you want. But there
is still a small helper that could be useful to you :
:func:`~openerp.web.Model.query`.

:func:`~openerp.web.Model.query` is a shortcut for the usual combination of
:py:meth:`~openerp.models.Model.search` and
::py:meth:`~openerp.models.Model.read` methods in Odoo models. It allows to
:search records and get their data with a shorter syntax. Example::

    model.query(['name', 'login', 'user_email', 'signature'])
         .filter([['active', '=', true], ['company_id', '=', main_company]])
         .limit(15)
         .all().then(function (users) {
        // do work with users records
    });

:func:`~openerp.web.Model.query` takes as argument a list of fields to query
in the model. It returns an instance of the :class:`openerp.web.Query` class.

:class:`~openerp.web.Query` is a class representing the query you are trying
to construct before sending it to the server. It has multiple methods you can
call to customize the query. All these methods will return the current
instance of :class:`~openerp.web.Query`:

* :func:`~openerp.web.Query.filter` allows to specify an Odoo *domain*. As a
  reminder, a domain in Odoo is a list of conditions, each condition is a list
  it self.
* :func:`~openerp.web.Query.limit` sets a limit to the number of records
  returned.

When you have customized you query, you can call the
:func:`~openerp.web.Query.all` method. It will performs the real query to the
server and return a deferred resolved with the result. The result is the same
thing return by the model's method :py:meth:`~openerp.models.Model.read` (a
list of dictionaries containing the asked fields).

Exercises
---------

.. exercise:: Message of the Day

    Create a widget ``MessageOfTheDay`` that will display the message
    contained in the last record of the ``message_of_the_day``. The widget
    should query the message as soon as it is inserted in the DOM and display
    the message to the user. Display that widget on the home page of the Odoo
    Pet Store module.

    .. only:: solutions

        .. code-block:: javascript

            openerp.oepetstore = function(instance) {
                var _t = instance.web._t,
                    _lt = instance.web._lt;
                var QWeb = instance.web.qweb;

                instance.oepetstore = {};

                instance.oepetstore.HomePage = instance.web.Widget.extend({
                    template: "HomePage",
                    start: function() {
                        var motd = new instance.oepetstore.MessageOfTheDay(this);
                        motd.appendTo(this.$el);
                    },
                });

                instance.web.client_actions.add('petstore.homepage', 'instance.oepetstore.HomePage');

                instance.oepetstore.MessageOfTheDay = instance.web.Widget.extend({
                    template: "MessageofTheDay",
                    init: function() {
                        this._super.apply(this, arguments);
                    },
                    start: function() {
                        var self = this;
                        new instance.web.Model("message_of_the_day").query(["message"]).first().then(function(result) {
                            self.$(".oe_mywidget_message_of_the_day").text(result.message);
                        });
                    },
                });

            }

        .. code-block:: xml

            <?xml version="1.0" encoding="UTF-8"?>

            <templates xml:space="preserve">
                <t t-name="HomePage">
                    <div class="oe_petstore_homepage">
                    </div>
                </t>
                <t t-name="MessageofTheDay">
                    <div class="oe_petstore_motd">
                        <p class="oe_mywidget_message_of_the_day"></p>
                    </div>
                </t>
            </templates>

        .. code-block:: css

            .oe_petstore_motd {
                margin: 5px;
                padding: 5px;
                border-radius: 3px;
                background-color: #F0EEEE;
            }

.. exercise:: Pet Toys List

    Create a widget ``PetToysList`` that will display 5 toys on the home page
    with their names and their images.

    In this Odoo addon, the pet toys are not stored in a new table like for
    the message of the day. They are in the table ``product.product``. If you
    click on the menu item :menuselection:`Pet Store --> Pet Store --> Pet
    Toys` you will be able to see them. Pet toys are identified by the
    category named ``Pet Toys``. You could need to document yourself on the
    model ``product.product`` to be able to create a domain to select pet toys
    and not all the products.

    To display the images of the pet toys, you should know that images in Odoo
    can be queried from the database like any other fields, but you will
    obtain a string containing Base64-encoded binary. There is a little trick
    to display images in Base64 format in HTML:

    .. code-block:: html

        <img class="oe_kanban_image" src="data:image/png;base64,${replace this by base64}"></image>

    The ``PetToysList`` widget should be displayed on the home page on the
    right of the ``MessageOfTheDay`` widget. You will need to make some layout
    with CSS to achieve this.

    .. only:: solutions

        .. code-block:: javascript

            openerp.oepetstore = function(instance) {
                var _t = instance.web._t,
                    _lt = instance.web._lt;
                var QWeb = instance.web.qweb;

                instance.oepetstore = {};

                instance.oepetstore.HomePage = instance.web.Widget.extend({
                    template: "HomePage",
                    start: function() {
                        var pettoys = new instance.oepetstore.PetToysList(this);
                        pettoys.appendTo(this.$(".oe_petstore_homepage_left"));
                        var motd = new instance.oepetstore.MessageOfTheDay(this);
                        motd.appendTo(this.$(".oe_petstore_homepage_right"));
                    },
                });

                instance.web.client_actions.add('petstore.homepage', 'instance.oepetstore.HomePage');

                instance.oepetstore.MessageOfTheDay = instance.web.Widget.extend({
                    template: "MessageofTheDay",
                    init: function() {
                        this._super.apply(this, arguments);
                    },
                    start: function() {
                        var self = this;
                        new instance.web.Model("message_of_the_day").query(["message"]).first().then(function(result) {
                            self.$(".oe_mywidget_message_of_the_day").text(result.message);
                        });
                    },
                });

                instance.oepetstore.PetToysList = instance.web.Widget.extend({
                    template: "PetToysList",
                    start: function() {
                        var self = this;
                        new instance.web.Model("product.product").query(["name", "image"])
                            .filter([["categ_id.name", "=", "Pet Toys"]]).limit(5).all().then(function(result) {
                            _.each(result, function(item) {
                                var $item = $(QWeb.render("PetToy", {item: item}));
                                self.$el.append($item);
                            });
                        });
                    },
                });

            }

        .. code-block:: xml

            <?xml version="1.0" encoding="UTF-8"?>

            <templates xml:space="preserve">
                <t t-name="HomePage">
                    <div class="oe_petstore_homepage">
                        <div class="oe_petstore_homepage_left"></div>
                        <div class="oe_petstore_homepage_right"></div>
                    </div>
                </t>
                <t t-name="MessageofTheDay">
                    <div class="oe_petstore_motd">
                        <p class="oe_mywidget_message_of_the_day"></p>
                    </div>
                </t>
                <t t-name="PetToysList">
                    <div class="oe_petstore_pettoyslist">
                    </div>
                </t>
                <t t-name="PetToy">
                    <div class="oe_petstore_pettoy">
                        <p><t t-esc="item.name"/></p>
                        <p><img t-att-src="'data:image/jpg;base64,'+item.image"/></p>
                    </div>
                </t>
            </templates>

        .. code-block:: css

            .oe_petstore_homepage {
                display: table;
            }

            .oe_petstore_homepage_left {
                display: table-cell;
                width : 300px;
            }

            .oe_petstore_homepage_right {
                display: table-cell;
                width : 300px;
            }

            .oe_petstore_motd {
                margin: 5px;
                padding: 5px;
                border-radius: 3px;
                background-color: #F0EEEE;
            }

            .oe_petstore_pettoyslist {
                padding: 5px;
            }

            .oe_petstore_pettoy {
                margin: 5px;
                padding: 5px;
                border-radius: 3px;
                background-color: #F0EEEE;
            }


Existing web components
-----------------------

In the previous part, we explained the Odoo web framework, a development
framework to create and architecture graphical JavaScript applications. The
current part is dedicated to the existing components of the Odoo web client
and most notably those containing entry points for developers to create new
widgets that will be inserted inside existing views or components.

The Action Manager
%%%%%%%%%%%%%%%%%%

To display a view or show a popup, as example when you click on a menu button,
Odoo use the concept of actions.  Actions are pieces of information explaining
what the web client should do. They can be loaded from the database or created
on-the-fly. The component handling actions in the web client is the *Action
Manager*.

Using the Action Manager
''''''''''''''''''''''''

A way to launch an action is to use a menu element targeting an action
registered in the database. As a reminder, here is how is defined a typical
action and its associated menu item:

.. code-block:: xml

    <record model="ir.actions.act_window" id="message_of_the_day_action">
        <field name="name">Message of the day</field>
        <field name="res_model">message_of_the_day</field>
        <field name="view_type">form</field>
        <field name="view_mode">tree,form</field>
    </record>

    <menuitem id="message_day" name="Message of the day" parent="petstore_menu"
        action="message_of_the_day_action"/>

It is also possible to ask the Odoo client to load an action from a JavaScript
code. To do so you have to create a dictionary explaining the action and then
to ask the action manager to re-dispatch the web client to the new action.  To
send a message to the action manager, :class:`~openerp.web.Widget` has a
shortcut that will automatically find the current action manager and execute
the action. Here is an example call to that method::

    instance.web.TestWidget = instance.web.Widget.extend({
        dispatch_to_new_action: function() {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: "product.product",
                res_id: 1,
                views: [[false, 'form']],
                target: 'current',
                context: {},
            });
        },
    });

The method to call to ask the action manager to execute a new action is
:func:`~openerp.web.Widget.do_action`. It receives as argument a dictionary
defining the properties of the action. Here is a description of the most usual
properties (not all of them may be used by all type of actions):

* ``type``: The type of the action, which means the name of the model in which
  the action is stored. As example, use ``ir.actions.act_window`` to show
  views and ``ir.actions.client`` for client actions.
* ``res_model``: For ``act_window`` actions, it is the model used by the
  views.
* ``res_id``: The ``id`` of the record to display.
* ``views``: For ``act_window`` actions, it is a list of the views to
  display. This argument must be a list of tuples with two components. The
  first one must be the identifier of the view (or ``false`` if you just want
  to use the default view defined for the model). The second one must be the
  type of the view.
* ``target``: If the value is ``current``, the action will be opened in the
  main content part of the web client. The current action will be destroyed
  before loading the new one. If it is ``new``, the action will appear in a
  popup and the current action will not be destroyed.
* ``context``: The context to use.

.. exercise:: Jump to Product

    Modify the ``PetToysList`` component developed in the previous part to
    jump to a form view displaying the shown item when we click on the item in
    the list.

    .. only:: solutions

        .. code-block:: javascript

            instance.oepetstore.PetToysList = instance.web.Widget.extend({
                template: "PetToysList",
                start: function() {
                    var self = this;
                    new instance.web.Model("product.product").query(["name", "image"])
                        .filter([["categ_id.name", "=", "Pet Toys"]]).limit(5).all().then(function(result) {
                        _.each(result, function(item) {
                            var $item = $(QWeb.render("PetToy", {item: item}));
                            self.$el.append($item);
                            $item.click(function() {
                                self.item_clicked(item);
                            });
                        });
                    });
                },
                item_clicked: function(item) {
                    this.do_action({
                        type: 'ir.actions.act_window',
                        res_model: "product.product",
                        res_id: item.id,
                        views: [[false, 'form']],
                        target: 'current',
                        context: {},
                    });
                },
            });

Client Actions
%%%%%%%%%%%%%%

In the module installed during the previous part of this guide, we defined a
simple widget that was displayed when we clicked on a menu element. This is
because this widget was registered as a *client action*. Client actions are a
type of action that are completely defined by JavaScript code. Here is a
reminder of the way we defined this client action::

    instance.oepetstore.HomePage = instance.web.Widget.extend({
        start: function() {
            console.log("pet store home page loaded");
        },
    });

    instance.web.client_actions.add('petstore.homepage', 'instance.oepetstore.HomePage');

``instance.web.client_actions`` is an instance of the
:class:`~openerp.web.Registry` class. Registries are not very different to
simple dictionaries, except they assign strings to class names. Adding the
``petstore.homepage`` key to this registry simply tells the web client "If
someone asks you to open a client action with key ``petstore.homepage``,
instantiate the ``instance.oepetstore.HomePage`` class and show it to the
user".

Here is how the menu element to show this client action was defined:

.. code-block:: xml

    <record id="action_home_page" model="ir.actions.client">
        <field name="tag">petstore.homepage</field>
    </record>

    <menuitem id="home_page_petstore_menu" name="Home Page" parent="petstore_menu"
        action="action_home_page"/>

Client actions do not need a lot of information except their type, which is
stored in the ``tag`` field.

When the web client wants to display a client action, it will simply show it
in the main content block of the web client. This is completely sufficient to
allow the widget to display anything and so create a completely new feature
for the web client.

Architecture of the Views
%%%%%%%%%%%%%%%%%%%%%%%%%

Most of the complexity of the web client resides in views. They are the basic
tools to display the data in the database.  The part will explain the views
and how those are displayed in the web client.

The View Manager
''''''''''''''''

Previously we already explained the purpose of the *Action Manager*. It is a
component, whose class is ``ActionManager``, that will handle the Odoo actions
(notably the actions associated with menu buttons).

When an ``ActionManager`` instance receive an action with type
``ir.actions.act_window``, it knows it has to show one or more views
associated with a precise model. To do so, it creates a *View Manager* that
will create one or multiple *Views*. See this diagram:

.. image:: web/viewarchitecture.*
   :align: center
   :width: 40%

The ``ViewManager`` instance will instantiate each view class corresponding to
the views indicated in the ``ir.actions.act_window`` action. As example, the
class corresponding to the view type ``form`` is ``FormView``. Each view class
inherits the ``View`` abstract class.

The Views
'''''''''

All the typical type of views in Odoo (all those you can switch to using the
small buttons under the search input text) are represented by a class
extending the ``View`` abstract class. Note the *Search View* (the search
input text on the top right of the screen that typically appear in kanban and
list views) is also considered a type of view even if it doesn't work like the
others (you can not "switch to" the search view and it doesn't take the full
screen).

A view has the responsibility to load its XML view description from the server
and display it. Views are also given an instance of the ``DataSet``
class. That class contains a list of identifiers corresponding to records that
the view should display. It is filled by the search view and the current view
is supposed to display the result of each search after it was performed by the
search view.

The Form View Fields
%%%%%%%%%%%%%%%%%%%%

A typical need in the web client is to extend the form view to display more
specific widgets. One of the possibilities to do this is to define a new type
of *Field*.

A field, in the form view, is a type of widget designed to display and edit
the content of *one (and only one) field* in a single record displayed by the
form view. All data types available in models have a default implementation to
display and edit them in the form view. As example, the ``FieldChar`` class
allows to edit the ``char`` data type.

Other field classes simply provide an alternative widget to represent an
existing data type. A good example of this is the ``FieldEmail`` class. There
is no ``email`` type in the models of Odoo. That class is designed to display
a ``char`` field assuming it contains an email (it will show a clickable link
to directly send a mail to the person and will also check the validity of the
mail address).

Also note there is nothing that disallow a field class to work with more than
one data type. As example, the ``FieldSelection`` class works with both
``selection`` and ``many2one`` field types.

As a reminder, to indicate a precise field type in a form view XML
description, you just have to specify the ``widget`` attribute:

.. code-block:: xml

    <field name="contact_mail" widget="email"/>

It is also a good thing to notice that the form view field classes are also
used in the editable list views. So, by defining a new field class, it make
this new widget available in both views.

Another type of extension mechanism for the form view is the *Form Widget*,
which has fewer restrictions than the fields (even though it can be more
complicated to implement). Form widgets will be explained later in this guide.

Fields are instantiated by the form view after it has read its XML description
and constructed the corresponding HTML representing that description. After
that, the form view will communicate with the field objects using some
methods. Theses methods are defined by the ``FieldInterface``
interface. Almost all fields inherit the ``AbstractField`` abstract
class. That class defines some default mechanisms that need to be implemented
by most fields.

Here are some of the responsibilities of a field class:

* The field class must display and allow the user to edit the value of the field.
* It must correctly implement the 3 field attributes available in all fields
  of Odoo. The ``AbstractField`` class already implements an algorithm that
  dynamically calculates the value of these attributes (they can change at any
  moment because their value change according to the value of other
  fields). Their values are stored in *Widget Properties* (the widget
  properties were explained earlier in this guide). It is the responsibility
  of each field class to check these widget properties and dynamically adapt
  depending of their values. Here is a description of each of these
  attributes:

  * ``required``: The field must have a value before saving. If ``required``
    is ``true`` and the field doesn't have a value, the method
    ``is_valid()`` of the field must return ``false``.
  * ``invisible``: When this is ``true``, the field must be invisible. The
    ``AbstractField`` class already has a basic implementation of this
    behavior that fits most fields.
  * ``readonly``: When ``true``, the field must not be editable by the
    user. Most fields in Odoo have a completely different behavior depending
    on the value of ``readonly``. As example, the ``FieldChar`` displays an
    HTML ``<input>`` when it is editable and simply displays the text when
    it is read-only. This also means it has much more code it would need to
    implement only one behavior, but this is necessary to ensure a good user
    experience.

* Fields have two methods, ``set_value()`` and ``get_value()``, which are
  called by the form view to give it the value to display and get back the new
  value entered by the user. These methods must be able to handle the value as
  given by the Odoo server when a ``read()`` is performed on a model and give
  back a valid value for a ``write()``.  Remember that the JavaScript/Python
  data types used to represent the values given by ``read()`` and given to
  ``write()`` is not necessarily the same in Odoo. As example, when you read a
  many2one, it is always a tuple whose first value is the id of the pointed
  record and the second one is the name get (ie: ``(15, "Agrolait")``). But
  when you write a many2one it must be a single integer, not a tuple
  anymore. ``AbstractField`` has a default implementation of these methods
  that works well for simple data type and set a widget property named
  ``value``.

Please note that, to better understand how to implement fields, you are
strongly encouraged to look at the definition of the ``FieldInterface``
interface and the ``AbstractField`` class directly in the code of the Odoo web
client.

Creating a New Type of Field
''''''''''''''''''''''''''''

In this part we will explain how to create a new type of field. The example
here will be to re-implement the ``FieldChar`` class and explain progressively
each part.

Simple Read-Only Field
""""""""""""""""""""""

Here is a first implementation that will only be able to display a text. The
user will not be able to modify the content of the field.

.. code-block:: javascript

    instance.oepetstore.FieldChar2 = instance.web.form.AbstractField.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.set("value", "");
        },
        render_value: function() {
            this.$el.text(this.get("value"));
        },
    });

    instance.web.form.widgets.add('char2', 'instance.oepetstore.FieldChar2');

In this example, we declare a class named ``FieldChar2`` inheriting from
``AbstractField``. We also register this class in the registry
``instance.web.form.widgets`` under the key ``char2``. That will allow us to
use this new field in any form view by specifying ``widget="char2"`` in the
``<field/>`` tag in the XML declaration of the view.

In this example, we define a single method: ``render_value()``. All it does is
display the widget property ``value``.  Those are two tools defined by the
``AbstractField`` class. As explained before, the form view will call the
method ``set_value()`` of the field to set the value to display. This method
already has a default implementation in ``AbstractField`` which simply sets
the widget property ``value``. ``AbstractField`` also watch the
``change:value`` event on itself and calls the ``render_value()`` when it
occurs. So, ``render_value()`` is a convenience method to implement in child
classes to perform some operation each time the value of the field changes.

In the ``init()`` method, we also define the default value of the field if
none is specified by the form view (here we assume the default value of a
``char`` field should be an empty string).

Read-Write Field
""""""""""""""""

Fields that only display their content and don't give the possibility to the
user to modify it can be useful, but most fields in Odoo allow edition
too. This makes the field classes more complicated, mostly because fields are
supposed to handle both and editable and non-editable mode, those modes are
often completely different (for design and usability purpose) and the fields
must be able to switch from one mode to another at any moment.

To know in which mode the current field should be, the ``AbstractField`` class
sets a widget property named ``effective_readonly``. The field should watch
the changes in that widget property and display the correct mode
accordingly. Example::

    instance.oepetstore.FieldChar2 = instance.web.form.AbstractField.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.set("value", "");
        },
        start: function() {
            this.on("change:effective_readonly", this, function() {
                this.display_field();
                this.render_value();
            });
            this.display_field();
            return this._super();
        },
        display_field: function() {
            var self = this;
            this.$el.html(QWeb.render("FieldChar2", {widget: this}));
            if (! this.get("effective_readonly")) {
                this.$("input").change(function() {
                    self.internal_set_value(self.$("input").val());
                });
            }
        },
        render_value: function() {
            if (this.get("effective_readonly")) {
                this.$el.text(this.get("value"));
            } else {
                this.$("input").val(this.get("value"));
            }
        },
    });

    instance.web.form.widgets.add('char2', 'instance.oepetstore.FieldChar2');

.. code-block:: xml

    <t t-name="FieldChar2">
        <div class="oe_field_char2">
            <t t-if="! widget.get('effective_readonly')">
                <input type="text"></input>
            </t>
        </div>
    </t>

In the ``start()`` method (which is called right after a widget has been
appended to the DOM), we bind on the event ``change:effective_readonly``. That
will allow use to redisplay the field each time the widget property
``effective_readonly`` changes. This event handler will call
``display_field()``, which is also called directly in ``start()``. This
``display_field()`` was created specifically for this field, it's not a method
defined in ``AbstractField`` or any other class. This is the method we will
use to display the content of the field depending we are in read-only mode or
not.

From now on the conception of this field is quite typical, except there is a
lot of verifications to know the state of the ``effective_readonly`` property:

* In the QWeb template used to display the content of the widget, it displays
  an ``<input type="text" />`` if we are in read-write mode and nothing in
  particular in read-only mode.
* In the ``display_field()`` method, we have to bind on the ``change`` event
  of the ``<input type="text" />`` to know when the user has changed the
  value. When it happens, we call the ``internal_set_value()`` method with the
  new value of the field. This is a convenience method provided by the
  ``AbstractField`` class. That method will set a new value in the ``value``
  property but will not trigger a call to ``render_value()`` (which is not
  necessary since the ``<input type="text" />`` already contains the correct
  value).
* In ``render_value()``, we use a completely different code to display the
  value of the field depending if we are in read-only or in read-write mode.

.. exercise:: Create a Color Field

    Create a ``FieldColor`` class. The value of this field should be a string
    containing a color code like those used in CSS (example: ``#FF0000`` for
    red). In read-only mode, this color field should display a little block
    whose color corresponds to the value of the field. In read-write mode, you
    should display an ``<input type="color" />``. That type of ``<input />``
    is an HTML5 component that doesn't work in all browsers but works well in
    Google Chrome. So it's OK to use as an exercise.

    You can use that widget in the form view of the ``message_of_the_day``
    model for its field named ``color``. As a bonus, you can change the
    ``MessageOfTheDay`` widget created in the previous part of this guide to
    display the message of the day with the background color indicated in the
    ``color`` field.

    .. only:: solutions

        .. code-block:: javascript

            instance.oepetstore.FieldColor = instance.web.form.AbstractField.extend({
                init: function() {
                    this._super.apply(this, arguments);
                    this.set("value", "");
                },
                start: function() {
                    this.on("change:effective_readonly", this, function() {
                        this.display_field();
                        this.render_value();
                    });
                    this.display_field();
                    return this._super();
                },
                display_field: function() {
                    var self = this;
                    this.$el.html(QWeb.render("FieldColor", {widget: this}));
                    if (! this.get("effective_readonly")) {
                        this.$("input").change(function() {
                            self.internal_set_value(self.$("input").val());
                        });
                    }
                },
                render_value: function() {
                    if (this.get("effective_readonly")) {
                        this.$(".oe_field_color_content").css("background-color", this.get("value") || "#FFFFFF");
                    } else {
                        this.$("input").val(this.get("value") || "#FFFFFF");
                    }
                },
            });

            instance.web.form.widgets.add('color', 'instance.oepetstore.FieldColor');

        .. code-block:: xml

            <t t-name="FieldColor">
                <div class="oe_field_color">
                    <t t-if="widget.get('effective_readonly')">
                        <div class="oe_field_color_content" />
                    </t>
                    <t t-if="! widget.get('effective_readonly')">
                        <input type="color"></input>
                    </t>
                </div>
            </t>

        .. code-block:: css

            .oe_field_color_content {
                height: 20px;
                width: 50px;
                border: 1px solid black;
            }

The Form View Custom Widgets
%%%%%%%%%%%%%%%%%%%%%%%%%%%%

Form fields can be useful, but their purpose is to edit a single field. To
interact with the whole form view and have more liberty to integrate new
widgets in it, it is recommended to create a custom form widget.

Custom form widgets are widgets that can be added in any form view using a
specific syntax in the XML definition of the view. Example:

.. code-block:: xml

    <widget type="xxx" />

This type of widget will simply be created by the form view during the
creation of the HTML according to the XML definition. They have properties in
common with the fields (like the ``effective_readonly`` property) but they are
not assigned a precise field. And so they don't have methods like
``get_value()`` and ``set_value()``. They must inherit from the ``FormWidget``
abstract class.

The custom form widgets can also interact with the fields of the form view by
getting or setting their values using the ``field_manager`` attribute of
``FormWidget``. Here is an example usage::

    instance.oepetstore.WidgetMultiplication = instance.web.form.FormWidget.extend({
        start: function() {
            this._super();
            this.field_manager.on("field_changed:integer_a", this, this.display_result);
            this.field_manager.on("field_changed:integer_b", this, this.display_result);
            this.display_result();
        },
        display_result: function() {
            var result = this.field_manager.get_field_value("integer_a") *
                this.field_manager.get_field_value("integer_b");
            this.$el.text("a*b = " + result);
        }
    });

    instance.web.form.custom_widgets.add('multiplication', 'instance.oepetstore.WidgetMultiplication');

This example custom widget is designed to take the values of two existing
fields (those must exist in the form view) and print the result of their
multiplication. It also refreshes each time the value of any of those fields
changes.

The ``field_manager`` attribute is in fact the ``FormView`` instance
representing the form view. The methods that widgets can call on that form
view are documented in the code of the web client in the ``FieldManagerMixin``
interface.  The most useful features are:

* The method ``get_field_value()`` which returns the value of a field.
* When the value of a field is changed, for any reason, the form view will
  trigger an event named ``field_changed:xxx`` where ``xxx`` is the name of
  the field.
* Also, it is possible to change the value of the fields using the method
  ``set_values()``. This method takes a dictionary as first and only argument
  whose keys are the names of the fields to change and values are the new
  values.

.. exercise:: Show Coordinates on Google Map

    In this exercise we would like to add two new fields on the
    ``product.product`` model: ``provider_latitude`` and
    ``provider_longitude``. Those would represent coordinates on a map. We
    also would like you to create a custom widget able to display a map
    showing these coordinates.

    To display that map, you can simply use the Google Map service using an HTML code similar to this:

    .. code-block:: html

        <iframe width="400" height="300" src="https://maps.google.com/?ie=UTF8&amp;ll=XXX,YYY&amp;output=embed">
        </iframe>

    Just replace ``XXX`` with the latitude and ``YYY`` with the longitude.

    You should display those two new fields as well as the map widget in a new
    page of the notebook displayed in the product form view.

    .. only:: solutions

        .. code-block:: javascript

            instance.oepetstore.WidgetCoordinates = instance.web.form.FormWidget.extend({
                start: function() {
                    this._super();
                    this.field_manager.on("field_changed:provider_latitude", this, this.display_map);
                    this.field_manager.on("field_changed:provider_longitude", this, this.display_map);
                    this.display_map();
                },
                display_map: function() {
                    this.$el.html(QWeb.render("WidgetCoordinates", {
                        "latitude": this.field_manager.get_field_value("provider_latitude") || 0,
                        "longitude": this.field_manager.get_field_value("provider_longitude") || 0,
                    }));
                }
            });

            instance.web.form.custom_widgets.add('coordinates', 'instance.oepetstore.WidgetCoordinates');

        .. code-block:: xml

            <t t-name="WidgetCoordinates">
                <iframe width="400" height="300"
                    t-att-src="'https://maps.google.com/?ie=UTF8&amp;ll=' + latitude + ',' + longitude + '&amp;output=embed'">
                </iframe>
            </t>

.. exercise:: Get the Current Coordinate

    Now we would like to display an additional button to automatically set the
    coordinates to the location of the current user.

    To get the coordinates of the user, an easy way is to use the geolocation
    JavaScript API.  `See the online documentation to know how to use it`_.

    .. _See the online documentation to know how to use it: http://www.w3schools.com/html/html5_geolocation.asp

    Please also note that it wouldn't be very logical to allow the user to
    click on that button when the form view is in read-only mode. So, this
    custom widget should handle correctly the ``effective_readonly`` property
    just like any field. One way to do this would be to make the button
    disappear when ``effective_readonly`` is true.

    .. only:: solutions

        .. code-block:: javascript

            instance.oepetstore.WidgetCoordinates = instance.web.form.FormWidget.extend({
                start: function() {
                    this._super();
                    this.field_manager.on("field_changed:provider_latitude", this, this.display_map);
                    this.field_manager.on("field_changed:provider_longitude", this, this.display_map);
                    this.on("change:effective_readonly", this, this.display_map);
                    this.display_map();
                },
                display_map: function() {
                    var self = this;
                    this.$el.html(QWeb.render("WidgetCoordinates", {
                        "latitude": this.field_manager.get_field_value("provider_latitude") || 0,
                        "longitude": this.field_manager.get_field_value("provider_longitude") || 0,
                    }));
                    this.$("button").toggle(! this.get("effective_readonly"));
                    this.$("button").click(function() {
                        navigator.geolocation.getCurrentPosition(_.bind(self.received_position, self));
                    });
                },
                received_position: function(obj) {
                    var la = obj.coords.latitude;
                    var lo = obj.coords.longitude;
                    this.field_manager.set_values({
                        "provider_latitude": la,
                        "provider_longitude": lo,
                    });
                },
            });

            instance.web.form.custom_widgets.add('coordinates', 'instance.oepetstore.WidgetCoordinates');

        .. code-block:: xml

            <t t-name="WidgetCoordinates">
                <iframe width="400" height="300"
                    t-att-src="'https://maps.google.com/?ie=UTF8&amp;ll=' + latitude + ',' + longitude + '&amp;output=embed'">
                </iframe>
                <button>Get My Current Coordinate</button>
            </t>

.. _jQuery: http://jquery.org
.. _Underscore.js: http://underscorejs.org
