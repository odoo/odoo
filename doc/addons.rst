Developing OpenERP Web Addons
=============================

An OpenERP Web addon is simply a Python package with an openerp
descriptor (a ``__openerp__.py`` file) which follows a few structural
and namespacing rules.

Structure
---------

.. literalinclude:: addon-structure.txt

``__openerp__.py``
  The addon's descriptor, contains the following information:

  ``name: str``
    The addon name, in plain, readable english
  ``version: str``
    The addon version, following `Semantic Versioning`_ rules
  ``depends: [str]``
    A list of addons this addon needs to work correctly. ``base`` is
    an implied dependency if the list is empty.
  ``css: [str]``
    An ordered list of CSS files this addon provides and needs. The
    file paths are relative to the addon's root. Because the Web
    Client *may* perform concatenations and other various
    optimizations on CSS files, the order is important.
  ``js: [str]``
    An ordered list of Javascript files this addon provides and needs
    (including dependencies files). As with CSS files, the order is
    important as the Web Client *may* perform contatenations and
    minimizations of files.
  ``active: bool``
    Whether this addon should be enabled by default any time it is
    found, or whether it will be enabled through other means (on a
    by-need or by-installation basis for instance).

``controllers/``
  All of the Python controllers and JSON-RPC endpoints.

``static/``
  The static files directory, may be served via a separate web server.

``static/lib/``
  Third-party libraries used by the addon.

``static/src/{css,js,img,xml}``
  Location for (respectively) the addon's static CSS files, its JS
  files, its various image resources as well as the template files

``static/test``
  Javascript tests files

``test/``
  The directories in which all tests for the addon are located.

Some of these are guidelines (and not enforced by code), but it's
suggested that these be followed. Code which does not fit into these
categories can go wherever deemed suitable.

Namespacing
-----------

Python
++++++

Because addons are also Python packages, they're inherently namespaced
and nothing special needs to be done on that front.

JavaScript
++++++++++

The JavaScript side of an addon has to live in the namespace
``openerp.$addon_name``. For instance, everything created by the addon
``base`` lives in ``openerp.base``.

The root namespace of the addon is a function which takes a single
parameter ``openerp``, which is an OpenERP client instance. Objects
(as well as functions, registry instances, etc...) should be added on
the correct namespace on that object.

The root function will be called by the OpenERP Web client when
initializing the addon.

.. code-block:: javascript

    // root namespace of the openerp.example addon
    /** @namespace */
    openerp.example = function (openerp) {
        // basic initialization code (e.g. templates loading)
        openerp.example.SomeClass = openerp.base.Class.extend(
            /** @lends openerp.example.SomeClass# */{
            /**
             * Description for SomeClass's constructor here
             *
             * @constructs
             */
            init: function () {
                // SomeClass initialization code
            }
            // rest of SomeClass
        });

        // access an object in an other addon namespace to replace it
        openerp.base.SearchView = openerp.base.SearchView.extend({
            init: function () {
                this._super.apply(this, arguments);
                console.log('Search view initialized');
            }
        });
    }

Creating new standard roles
---------------------------

Views
+++++

Views are the standard high-level component in OpenERP. A view type corresponds
to a way to display a set of data (coming from an OpenERP model).

In OpenERP Web, views are standard objects registered against a dedicated
object registry, so the :js:class:`~openerp.base.ViewManager` knows where to
find and how to call them.

Although not mandatory, it is recommended that views inherit from
:js:class:`openerp.base.View`, which provides a view useful services to its
children.

Registering a view
~~~~~~~~~~~~~~~~~~

This is the first task to perform when creating a view, and the simplest by
far: simply call ``openerp.base.views.add(name, object_path)`` to register
the object of path ``object_path`` as the view for the view name ``name``.

The view name is the name you gave to your new view in the OpenERP server.

From that point onwards, OpenERP Web will be able to find your object and
instantiate it.

Standard view behaviors
~~~~~~~~~~~~~~~~~~~~~~~

In the normal OpenERP Web flow, views have to implement a number of methods so
view managers can correctly communicate with them:

``start()``
    This method will always be called after creating the view (via its
    constructor), but not necessarily immediately.

    It is called with no arguments and should handle the heavy setup work,
    including remote call (to load the view's setup data from the server via
    e.g. ``fields_view_get``, for instance).

    ``start`` should return a `promise object`_ which *must* be resolved when
    the view's setup is completed. This promise is used by view managers to
    know when they can start interacting with the view.

``do_hide()``
    Called by the view manager when it wants to replace this view by an other
    one, but wants to keep this view around to re-activate it later.

    Should put the view in some sort of hibernation mode, and *must* hide its
    DOM elements.

``do_show()``
    Called when the view manager wants to re-display the view after having
    hidden it. The view should refresh its data display upon receiving this
    notification

``do_search(domain: Array, context: Object, group_by: Array)``
    If the view is searchable, this method is called to notify it of a search
    against it.

    It should use the provided query data to perform a search and refresh its
    internal content (and display).

    All views are searchable by default, but they can be made non-searchable
    by setting the property ``searchable`` to ``false``.

    This can be done either on the view class itself (at the same level as
    defining e.g. the ``start`` method) or at the instance level (in the
    class's ``init``), though you should generally set it on the class.

Frequent development tasks
--------------------------

There are a number of tasks which OpenERP Web developers do or will need to
perform quite regularly. To make these easier, we have written a few guides
to help you get started:

.. toctree::
    :maxdepth: 1

    guides/client-action
    guides/sidebar-protocol

Translations
------------

OpenERP Web should provide most of the tools needed to correctly translate your
addons via the tool of your choice (OpenERP itself uses `Launchpad's own
translation tool`_.

Making strings translatable
+++++++++++++++++++++++++++

QWeb
~~~~

QWeb automatically marks all text nodes (any text which is not in an XML
attribute and not part of an XML tag) as translatable, and handles the
replacement for you. There is nothing special to do to mark template text as
translatable

JavaScript
~~~~~~~~~~

OpenERP Web provides two functions to translate human-readable strings in
javascript code. These functions should be "imported" in your module by
aliasing them to their bare name:

.. code-block:: javascript

    var _t = openerp.web._t,
       _tl = openerp.web._tl;

importing those functions under any other name is not guaranteed to work.

.. note:: only import them if necessary, and only the necessary one(s), no need
          to clutter your module's namespace for nothing

.. js:function:: openerp.web._t(s)

    Base translation function, eager, works much like :manpage:`gettext(3)`

    :type s: String
    :rtype: String

.. js:function:: openerp.web._lt(s)

    Lazy equivalent to :js:func:`~openerp.web._t`, this function will postpone
    fetching the translation to its argument until the last possible moment.

    To use in contexts evaluated before the translation database can be
    fetched, usually your module's toplevel and the attributes of classes
    defined in it (class attributes, not instance attributes set in the
    constructor).

    :type s: String
    :rtype: LazyString

Text formatting & translations
""""""""""""""""""""""""""""""

A difficulty when translating is integrating data (from the code) into the
translated string. In OpenERP Web addons, this should be done by wrapping the
text to translate in an :manpage:`sprintf(3)` call. For OpenERP Web,
:manpage:`sprintf(3)` is provided by `underscore.string
<http://epeli.github.com/underscore.string/>`_.

As much as possible, you should use the "named argument" form of sprintf:

.. code-block:: javascript

    var translated_string = _.str.sprintf(
        _t("[%(first_record)d to %(last_record)d] of %(records_count)d"), {
            first_record: first + 1,
            last_record: last,
            records_count: total
        }));

named arguments make the string to translate much clearer for translators, and
allows them to "move" sections around based on the requirements of their
language (not all language order text like english).

Named arguments are specified using the following pattern: ``%($name)$type``
where

``$name``
  the name of the argument, this is the key in the object/dictionary provided
  as second parameter to ``sprintf``
``$type``
  a type/format specifier, `see the list for all possible types
  <http://www.diveintojavascript.com/projects/javascript-sprintf>`_.

.. note:: positional arguments are acceptable if the translated string has
          *a single* argument and its content is easy to guess from the text
          around it. Named arguments should still be preferred.

.. warning:: you should *never* use string concatenation as it robs the
             translator of context and make result in a completely incorrect
             translation

Extracting strings
~~~~~~~~~~~~~~~~~~

.. program:: gen_translations.sh

Once strings have been marked for translation, they need to be extracted into
:abbr:`POT (Portable Object Template)` files, from which most translation tools
can build a database.

This can be done via the provided :program:`gen_translations.sh`.

It can be called either as :option:`gen_translations.sh -a` or by providing
two parameters, a path to the addons and the complete path in which to put the
extracted POT file.

.. option:: -a

    Extracts translations from all standard OpenERP Web addons (addons bundled
    with OpenERP Web itself) and puts the extracted templates into the right
    directory for `Rosetta`_ to handle them

Utility behaviors
-----------------

JavaScript
++++++++++

* All javascript objects inheriting from
  :js:class:`openerp.base.BasicConroller` will have all methods
  starting with ``on_`` or ``do_`` bound to their ``this``. This means
  they don't have to be manually bound (via ``_.bind`` or ``$.proxy``)
  in order to be useable as bound event handlers (event handlers
  keeping their object as ``this`` rather than taking whatever
  ``this`` object they were called with).

  Beware that this is only valid for methods starting with ``do_`` and
  ``on_``, any other method will have to be bound manually.

.. _addons-testing:

Testing
-------

Python
++++++

OpenERP Web uses unittest2_ for its testing needs. We selected
unittest2 rather than unittest_ for the following reasons:

* autodiscovery_ (similar to nose, via the ``unit2``
  CLI utility) and `pluggable test discovery`_.

* `new and improved assertions`_ (with improvements in type-specific
  inequality reportings) including `pluggable custom types equality
  assertions`_

* neveral new APIs, most notably `assertRaises context manager`_,
  `cleanup function registration`_, `test skipping`_ and `class- and
  module-level setup and teardown`_

* finally, unittest2 is a backport of Python 3's unittest. We might as
  well get used to it.

To run tests on addons (from the root directory of OpenERP Web) is as
simple as typing ``PYTHONPATH=. unit2 discover -s addons`` [#]_. To
test an addon which does not live in the ``addons`` directory, simply
replace ``addons`` by the directory in which your own addon lives.

.. note:: unittest2 is entirely compatible with nose_ (or the
     other way around). If you want to use nose as your test
     runner (due to its addons for instance) you can simply install it
     and run ``nosetests addons`` instead of the ``unit2`` command,
     the result should be exactly the same.

Python
++++++

.. autoclass:: web.common.session.OpenERPSession
    :members:

.. autoclass:: web.common.openerplib.main.Model
    :members:

* Addons lifecycle (loading, execution, events, ...)

  * Python-side
  * JS-side

* Handling static files
* Overridding a Python controller (object?)
* Overridding a Javascript controller (object?)
* Extending templates
  .. how do you handle deploying static files via e.g. a separate lighttpd?
* Python public APIs
* QWeb templates description?
* OpenERP Web modules (from OpenERP modules)

.. [#] the ``-s`` parameter tells ``unit2`` to start trying to
       find tests in the provided directory (here we're testing
       addons). However a side-effect of that is to set the
       ``PYTHONPATH`` there as well, so it will fail to find (and
       import) ``openerpweb``.

       The ``-t`` parameter lets us set the ``PYTHONPATH``
       independently, but it doesn't accept multiple values and here
       we really want to have both ``.`` and ``addons`` on the
       ``PYTHONPATH``.

       The solution is to set the ``PYTHONPATH`` to ``.`` on start,
       and the ``start-directory`` to ``addons``. This results in a
       correct ``PYTHONPATH`` within ``unit2``.

.. _unittest:
    http://docs.python.org/library/unittest.html

.. _unittest2:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml

.. _autodiscovery:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml#test-discovery

.. _pluggable test discovery:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml#load-tests

.. _new and improved assertions:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml#new-assert-methods

.. _pluggable custom types equality assertions:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml#add-new-type-specific-functions

.. _assertRaises context manager:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml#assertraises

.. _cleanup function registration:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml#cleanup-functions-with-addcleanup

.. _test skipping:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml#test-skipping

.. _class- and module-level setup and teardown:
    http://www.voidspace.org.uk/python/articles/unittest2.shtml#class-and-module-level-fixtures

.. _Semantic Versioning:
    http://semver.org/

.. _nose:
    http://somethingaboutorange.com/mrl/projects/nose/1.0.0/

.. _promise object:
    http://api.jquery.com/deferred.promise/

.. _Rosetta:
.. _Launchpad's own translation tool:
    https://help.launchpad.net/Translations
