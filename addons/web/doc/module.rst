.. _module:

Building an OpenERP Web module
==============================

There is no significant distinction between an OpenERP Web module and
an OpenERP module, the web part is mostly additional data and code
inside a regular OpenERP module. This allows providing more seamless
features by integrating your module deeper into the web client.

A Basic Module
--------------

A very basic OpenERP module structure will be our starting point:

.. code-block:: text

    web_example
    ├── __init__.py
    └── __openerp__.py

.. literalinclude:: module/__openerp__.py
    :language: python

This is a sufficient minimal declaration of a valid OpenERP module.

Web Declaration
---------------

There is no such thing as a "web module" declaration. An OpenERP
module is automatically recognized as "web-enabled" if it contains a
``static`` directory at its root, so:

.. code-block:: text

    web_example
    ├── __init__.py
    ├── __openerp__.py
    └── static

is the extent of it. You should also change the dependency to list
``web``:

.. literalinclude:: module/__openerp__.py.1.diff
    :language: diff

.. note::

    This does not matter in normal operation so you may not realize
    it's wrong (the web module does the loading of everything else, so
    it can only be loaded), but when e.g. testing the loading process
    is slightly different than normal, and incorrect dependency may
    lead to broken code.

This makes the "web" discovery system consider the module as having a
"web part", and check if it has web controllers to mount or javascript
files to load. The content of the ``static/`` folder is also
automatically made available to web browser at the URL
``$module-name/static/$file-path``. This is sufficient to provide
pictures (of cats, usually) through your module. However there are
still a few more steps to running javascript code.

Getting Things Done
-------------------

The first one is to add javascript code. It's customary to put it in
``static/src/js``, to have room for e.g. other file types, or
third-party libraries.

.. literalinclude:: module/static/src/js/first_module.js
    :language: javascript

The client won't load any file unless specified, thus the new file
should be listed in the module's manifest file, under a new key ``js``
(a list of file names, or glob patterns):

.. literalinclude:: module/__openerp__.py.2.diff
    :language: diff

At this point, if the module is installed and the client reloaded the
message should appear in your browser's development console.

.. note::

    Because the manifest file has been edited, you will have to
    restart the OpenERP server itself for it to be taken in account.

    You may also want to open your browser's console *before*
    reloading, depending on the browser messages printed while the
    console is closed may not work or may not appear after opening it.

.. note::

    If the message does not appear, try cleaning your browser's caches
    and ensure the file is correctly loaded from the server logs or
    the "resources" tab of your browser's developers tools.

At this point the code runs, but it runs only once when the module is
initialized, and it can't get access to the various APIs of the web
client (such as making RPC requests to the server). This is done by
providing a `javascript module`_:

.. literalinclude:: module/static/src/js/first_module.js.1.diff
    :language: diff

If you reload the client, you'll see a message in the console exactly
as previously. The differences, though invisible at this point, are:

* All javascript files specified in the manifest (only this one so
  far) have been fully loaded
* An instance of the web client and a namespace inside that instance
  (with the same name as the module) have been created and are
  available for use

The latter point is what the ``instance`` parameter to the function
provides: an instance of the OpenERP Web client, with the contents of
all the new module's dependencies loaded in and initialized. These are
the entry points to the web client's APIs.

To demonstrate, let's build a simple :doc:`client action
<client_action>`: a stopwatch

First, the action declaration:

.. literalinclude:: module/__openerp__.py.3.diff
    :language: diff

.. literalinclude:: module/web_example.xml
    :language: xml

then set up the :doc:`client action hook <client_action>` to register
a function (for now):

.. literalinclude:: module/static/src/js/first_module.js.2.diff
    :language: diff

Updating the module (in order to load the XML description) and
re-starting the server should display a new menu *Example Client
Action* at the top-level. Opening said menu will make the message
appear, as usual, in the browser's console.

Paint it black
--------------

The next step is to take control of the page itself, rather than just
print little messages in the console. This we can do by replacing our
client action function by a :doc:`widget`. Our widget will simply use
its :js:func:`~openerp.web.Widget.start` to add some content to its
DOM:

.. literalinclude:: module/static/src/js/first_module.js.3.diff
    :language: diff

after reloading the client (to update the javascript file), instead of
printing to the console the menu item clears the whole screen and
displays the specified message in the page.

Since we've added a class on the widget's :ref:`DOM root
<widget-dom_root>` we can now see how to add a stylesheet to a module:
first create the stylesheet file:

.. literalinclude:: module/static/src/css/web_example.css
    :language: css

then add a reference to the stylesheet in the module's manifest (which
will require restarting the OpenERP Server to see the changes, as
usual):

.. literalinclude:: module/__openerp__.py.4.diff
    :language: diff

the text displayed by the menu item should now be huge, and
white-on-black (instead of small and black-on-white). From there on,
the world's your canvas.

.. note::

    Prefixing CSS rules with both ``.openerp`` (to ensure the rule
    will apply only within the confines of the OpenERP Web client) and
    a class at the root of your own hierarchy of widgets is strongly
    recommended to avoid "leaking" styles in case the code is running
    embedded in an other web page, and does not have the whole screen
    to itself.

So far we haven't built much (any, really) DOM content. It could all
be done in :js:func:`~openerp.web.Widget.start` but that gets unwieldy
and hard to maintain fast. It is also very difficult to extend by
third parties (trying to add or change things in your widgets) unless
broken up into multiple methods which each perform a little bit of the
rendering.

The first way to handle this method is to delegate the content to
plenty of sub-widgets, which can be individually overridden. An other
method [#DOM-building]_ is to use `a template
<http://en.wikipedia.org/wiki/Web_template>`_ to render a widget's
DOM.

OpenERP Web's template language is :doc:`qweb`. Although any
templating engine can be used (e.g. `mustache
<http://mustache.github.com/>`_ or `_.template
<http://underscorejs.org/#template>`_) QWeb has important features
which other template engines may not provide, and has special
integration to OpenERP Web widgets.

Adding a template file is similar to adding a style sheet:

.. literalinclude:: module/static/src/xml/web_example.xml
    :language: xml

.. literalinclude:: module/__openerp__.py.5.diff
    :language: diff

The template can then easily be hooked in the widget:

.. literalinclude:: module/static/src/js/first_module.js.4.diff
    :language: diff

And finally the CSS can be altered to style the new (and more complex)
template-generated DOM, rather than the code-generated one:

.. literalinclude:: module/static/src/css/web_example.css.1.diff
    :language: diff

.. note::

    The last section of the CSS change is an example of "state
    classes": a CSS class (or set of classes) on the root of the
    widget, which is toggled when the state of the widget changes and
    can perform drastic alterations in rendering (usually
    showing/hiding various elements).

    This pattern is both fairly simple (to read and understand) and
    efficient (because most of the hard work is pushed to the
    browser's CSS engine, which is usually highly optimized, and done
    in a single repaint after toggling the class).

The last step (until the next one) is to add some behavior and make
our stopwatch watch. First hook some events on the buttons to toggle
the widget's state:

.. literalinclude:: module/static/src/js/first_module.js.5.diff
    :language: diff

This demonstrates the use of the "events hash" and event delegation to
declaratively handle events on the widget's DOM. And already changes
the button displayed in the UI. Then comes some actual logic:

.. literalinclude:: module/static/src/js/first_module.js.6.diff
    :language: diff

* An initializer (the ``init`` method) is introduced to set-up a few
  internal variables: ``_start`` will hold the start of the timer (as
  a javascript Date object), and ``_watch`` will hold a ticker to
  update the interface regularly and display the "current time".

* ``update_counter`` is in charge of taking the time difference
  between "now" and ``_start``, formatting as ``HH:MM:SS`` and
  displaying the result on screen.

* ``watch_start`` is augmented to initialize ``_start`` with its value
  and set-up the update of the counter display every 33ms.

* ``watch_stop`` disables the updater, does a final update of the
  counter display and resets everything.

* Finally, because javascript Interval and Timeout objects execute
  "outside" the widget, they will keep going even after the widget has
  been destroyed (especially an issue with intervals as they repeat
  indefinitely). So ``_watch`` *must* be cleared when the widget is
  destroyed (then the ``_super`` must be called as well in order to
  perform the "normal" widget cleanup).

Starting and stopping the watch now works, and correctly tracks time
since having started the watch, neatly formatted.

.. [#DOM-building] they are not alternative solutions: they work very
                   well together. Templates are used to build "just
                   DOM", sub-widgets are used to build DOM subsections
                   *and* delegate part of the behavior (e.g. events
                   handling).

.. _javascript module:
    http://addyosmani.com/resources/essentialjsdesignpatterns/book/#modulepatternjavascript
