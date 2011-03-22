Developing OpenERP Web Addons
=============================

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

  The third-party dependencies should be bundled in it (each in their
  own directory).

``static/openerp/``
  Sub-tree for all the addon's own static files.

``static/openerp/{css,js,img}``
  Location for (respectively) the addon's static CSS files, its JS
  files and its various image resources.

``tests/``
  The directories in which all tests for the addon are located.

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

APIs
----

Javascript
++++++++++

.. js:class:: openerp.base.Widget(view, node)

    :param openerp.base.Controller view: The view to which the widget belongs
    :param Object node: the ``fields_view_get`` descriptor for the widget

.. js:attribute:: openerp.base.Widget.$element

    The widget's root element as jQuery object

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
