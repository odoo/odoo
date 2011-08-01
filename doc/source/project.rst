The OpenERP Web open-source project
===================================

Getting involved
----------------

Translations
++++++++++++

Bug reporting
+++++++++++++

Source code repository
++++++++++++++++++++++

Merge proposals
+++++++++++++++

Coding issues and coding conventions
++++++++++++++++++++++++++++++++++++

Javascript coding
~~~~~~~~~~~~~~~~~

These are a number of guidelines for javascript code. More than coding
conventions, these are warnings against potentially harmful or sub-par
constructs.

Ideally, you should be able to configure your editor or IDE to warn you against
these kinds of issues.

Use ``var`` for *all* declarations
**********************************

In javascript (as opposed to Python), assigning to a variable which does not
already exist and is not explicitly declared (via ``var``) will implicitly
create a global variable. This is bad for a number of reasons:

* It leaks information outside function scopes
* It keeps memory of previous run, with potentially buggy behaviors
* It may conflict with other functions with the same issue
* It makes code harder to statically check (via e.g. IDE inspectors)

.. note::
    It is perfectly possible to use ``var`` in ``for`` loops:

    .. code-block:: javascript

        for (var i = 0; i < some_array.length; ++i) {
            // code here
        }

    this is not an issue

All local *and global* variables should be declared via ``var``.

.. note:: generally speaking, you should not need globals in OpenERP Web: you
          can just declare a variable local to your top-level function. This
          way, if your widget/addon is instantiated several times on the same
          page (because it's used in embedded mode) each instance will have its
          own internal but global-to-its-objects data.

Do not leave trailing commas in object literals
***********************************************

While it is legal to leave trailing commas in Python dictionaries, e.g.

.. code-block:: python

    foo = {
        'a': 1,
        'b': 2,
    }

and it's valid in ECMAScript 5 and most browsers support it in Javascript, you
should *never* use trailing commas in Javascript object literals:

* Internet Explorer does *not* support trailing commas (at least until and
  including Internet Explorer 8), and trailing comma will cause hard-to-debug
  errors in it

* JSON does not accept trailing comma (it is a syntax error), and using them
  in object literals puts you at risks of using them in literal JSON strings
  as well (though there are few reasons to write JSON by hand)

*Never* use ``for … in`` to iterate on arrays
*********************************************

:ref:`Iterating over an object with for…in is a bit tricky already
<for-in-iteration>`, it is far more complex than in Python (where it Just
Works™) due to the interaction of various Javascript features, but to iterate
on arrays it becomes downright deadly and errorneous: ``for…in`` really
iterates over an *object*'s *properties*.

With an array, this has the following consequences:

* It does not necessarily iterate in numerical order, nor does it iterate in
  any kind of set order. The order is implementation-dependent and may vary
  from one run to the next depending on a number of reasons and implementation
  details.
* If properties are added to an array, to ``Array.prototype`` or to
  ``Object.prototype`` (the latter two should not happen in well-behaved
  javascript code, but you never know...) those properties *will* be iterated
  over by ``for…in``. While ``Object.hasOwnProperty`` will guard against
  iterating prototype properties, they will not guard against properties set
  on the array instance itself (as memoizers for instance).

  Note that this includes setting negative keys on arrays.

For this reason, ``for…in`` should **never** be used on array objects. Instead,
you should use either a normal ``for`` or (even better, unless you have
profiled the code and found a hotspot) one of Underscore's array iteration
methods (`_.each`_, `_.map`_, `_.filter`_, etc...).

Underscore is guaranteed to be bundled and available in OpenERP Web scopes.

.. _for-in-iteration:

Use ``hasOwnProperty`` when iterating on an object with ``for … in``
********************************************************************

``for…in`` is Javascript's built-in facility for iterating over and object's
properties.

`It is also fairly tricky to use`_: it iterates over *all* non-builtin
properties of your objects [#]_, which includes methods of an object's class.

As a result, when iterating over an object with ``for…in`` the first line of
the body *should* generally be a call to `Object.hasOwnProperty`_. This call
will check whether the property was set directly on the object or comes from
the object's class:

.. code-block:: javascript

    for(var key in ob) {
        if (!ob.hasOwnProperty(key)) {
            // comes from ob's class
            continue;
        }
        // do stuff with key
    }

Since properties can be added directly to e.g. ``Object.prototype`` (even
though it's usually considered bad style), you should not assume you ever know
which properties ``for…in`` is going to iterate over.

An alternative is to use Underscore's iteration methods, which generally work
over objects as well as arrays:

Instead of

.. code-block:: javascript

    for (var key in ob) {
        if (!ob.hasOwnProperty(key)) { continue; }
        var value = ob[key];
        // Do stuff with key and value
    }

you could write:

.. code-block:: javascript

    _.each(ob, function (value, key) {
        // do stuff with key and value
    });

and not worry about the details of the iteration: underscore should do the
right thing for you on its own [#]_.

Writing documentation
+++++++++++++++++++++

The OpenERP Web project documentation uses Sphinx_ for the literate
documentation (this document for instance), the development guides
(for Python and Javascript alike) and the Python API documentation
(via autodoc_).

For the Javascript API, documentation should be written using the
`JsDoc Toolkit`_.

Guides and main documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The meat and most important part of all documentation. Should be
written in plain English, using reStructuredText_ and taking advantage
of `Sphinx's extensions`_, especially `cross-references`_.

Python API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~

All public objects in Python code should have a docstring written in
RST, using Sphinx's `Python domain`_ [#]_:

* Functions and methods documentation should be in their own
  docstring, using Sphinx's `info fields`_

  For parameters types, built-in and stdlib types should be using the
  combined syntax:

  .. code-block:: restructuredtext

      :param dict foo: what the purpose of foo is

  unless a more extensive explanation needs to be given (e.g. the
  specification that the input should be a list of 3-tuple needs to
  use ``:type:`` even though all types involved are built-ins). Any
  other type should be specified in full using the ``:type:`` field

  .. code-block:: restructuredtext

      :param foo: what the purpose of foo is
      :type foo: some.addon.Class

  Mentions of other methods (including within the same class), modules
  or types in descriptions (of anything, including parameters) should
  be cross-referenced.

* Classes should likewise be documented using their own docstring, and
  should include the documentation of their construction (``__init__``
  and ``__new__``), using the `info fields`_  as well.

* Attributes (class and instance) should be documented in their
  class's docstring via the ``.. attribute::`` directive, following
  the class's own documentation.

* The relation between modules and module-level attributes is similar:
  modules should be documented in their own docstring, public module
  attributes should be documented in the module's docstring using the
  ``.. data::`` directive.

Javascript API documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Javascript API documentation uses JsDoc_, a javascript documentation
toolkit with a syntax similar to (and inspired by) JavaDoc's.

Due to limitations of JsDoc, the coding patterns in OpenERP Web and
the Sphinx integration, there are a few peculiarities to be aware of
when writing javascript API documentation:

* Namespaces and classes *must* be explicitly marked up even if they
  are not documented, or JsDoc will not understand what they are and
  will not generate documentation for their content.

  As a result, the bare minimum for a namespace is:

  .. code-block:: javascript

      /** @namespace */
      foo.bar.baz = {};

  while for a class it is:

  .. code-block:: javascript

      /** @class */
      foo.bar.baz.Qux = [...]

* Because the OpenERP Web project uses `John Resig's Class
  implementation`_ instead of direct prototypal inheritance [#]_,
  JsDoc fails to infer class scopes (and constructors or super
  classes, for that matter) and has to be told explicitly.

  See :ref:`js-class-doc` for the complete rundown.

* Much like the JavaDoc, JsDoc does not include a full markup
  language. Instead, comments are simply marked up in HTML.

  This has a number of inconvenients:

  * Complex documentation comments become nigh-unreadable to read in
    text editors (as opposed to IDEs, which may handle rendering
    documentation comments on the fly)

  * Though cross-references are supported by JsDoc (via ``@link`` and
    ``@see``), they only work within the JsDoc

  * More general impossibility to integrate correctly with Sphinx, and
    e.g. reference JavaScript objects from a tutorial, or have all the
    documentation live at the same place.

  As a result, JsDoc comments should be marked up using RST, not
  HTML. They may use Sphinx's cross-references as well.

.. _js-class-doc:

Documenting a Class
*******************

The first task when documenting a class using JsDoc is to *mark* that
class, so JsDoc knows it can be used to instantiate objects (and, more
importantly as far as it's concerned, should be documented with
methods and attributes and stuff).

This is generally done through the ``@class`` tag, but this tag has a
significant limitation: it "believes" the constructor and the class
are one and the same [#]_. This will work for constructor-less
classes, but because OpenERP Web uses Resig's class the constructor is
not the class itself but its ``init()`` method.

Because this pattern is common in modern javascript code bases, JsDoc
supports it: it is possible to mark an arbitrary instance method as
the *class specification* by using the ``@constructs`` tag.

.. warning:: ``@constructs`` is a class specification in and of
    itself, it *completely replaces* the class documentation.

    Using both a class documentation (even without ``@class`` itself)
    and a constructor documentation is an *error* in JsDoc and will
    result in incorrect behavior and broken documentation.

The second issue is that Resig's class uses an object literal to
specify instance methods, and because JsDoc does not know anything
about Resig's class, it does not know about the role of the object
literal.

As with constructors, though, JsDoc provides a pluggable way to tell
it about methods: the ``@lends`` tag. It specifies that the object
literal "lends" its properties to the class being built.

``@lends`` must be specified right before the opening brace of the
object literal (between the opening paren of the ``#extend`` call and
the brace), and takes the full qualified name of the class being
created as a parameter, followed by the character ``#`` or by
``.prototype``. This latter part tells JsDoc these are instance
methods, not class (static) methods..

Finally, specifying a class's superclass is done through the
``@extends`` tag, which takes a fully qualified class name as a
parameter.

Here are a class without a constructor, and a class with one, so that
everything is clear (these are straight from the OpenERP Web source,
with the descriptions and irrelevant atttributes stripped):

.. code-block:: javascript

    /**
     * <Insert description here, not below>
     *
     * @class
     * @extends openerp.base.search.Field
     */
    openerp.base.search.CharField = openerp.base.search.Field.extend(
        /** @lends openerp.base.search.CharField# */ {
            // methods here
    });

.. code-block:: javascript

    openerp.base.search.Widget = openerp.base.Controller.extend(
        /** @lends openerp.base.search.Widget# */{
        /**
         * <Insert description here, not below>
         *
         * @constructs
         * @extends openerp.base.Controller
         *
         * @param view the ancestor view of this widget
         */
        init: function (view) {
            // construction of the instance
        },
        // bunch of other methods
    });

OpenERP Web over time
---------------------

Release process
+++++++++++++++

OpenSUSE packaging: http://blog.lowkster.com/2011/04/packaging-python-packages-in-opensuse.html

Roadmap
+++++++

Release notes
+++++++++++++

.. [#] More precisely, it iterates over all *enumerable* properties. It just
       happens that built-in properties (such as ``String.indexOf`` or
       ``Object.toString``) are set to non-enumerable.

       The enumerability of a property can be checked using
       `Object.propertyIsEnumeable`_.

       Before ECMAScript 5, it was not possible for user-defined properties
       to be non-enumerable in a portable manner. ECMAScript 5 introduced
       `Object.defineProperty`_ which lets user code create non-enumerable
       properties (and more, read-only properties for instance, or implicit
       getters and setters). However, support for these is not fully complete
       at this point, and they are not being used in OpenERP Web code anyway.

.. [#] While using underscore is generally the preferred method (simpler,
       more reliable and easier to write than a *correct* ``for…in``
       iteration), it is also probably slower (due to the overhead of
       calling a bunch of functions).

       As a result, if you profile some code and find out that an underscore
       method adds unacceptable overhead in a tight loop, you may want to
       replace it with a ``for…in`` (or a regular ``for`` statement for
       arrays).

.. [#] Because Python is the default domain, the ``py:`` markup prefix
       is optional and should be left out.

.. [#] Resig's Class still uses prototypes under the hood, it doesn't
       reimplement its own object system although it does add several
       helpers such as the ``_super()`` instance method.

.. [#] Which is the case in normal Javascript semantics. Likewise, the
       ``.prototype`` / ``#`` pattern we will see later on is due to
       JsDoc defaulting to the only behavior it can rely on: "normal"
       Javascript prototype-based type creation.

.. _reStructuredText:
    http://docutils.sourceforge.net/rst.html
.. _Sphinx:
    http://sphinx.pocoo.org/index.html
.. _Sphinx's extensions:
    http://sphinx.pocoo.org/markup/index.html
.. _Python domain:
    http://sphinx.pocoo.org/domains.html#the-python-domain
.. _info fields:
    http://sphinx.pocoo.org/domains.html#info-field-lists
.. _autodoc:
    http://sphinx.pocoo.org/ext/autodoc.html
        ?highlight=autodoc#sphinx.ext.autodoc
.. _cross-references:
    http://sphinx.pocoo.org/markup/inline.html#xref-syntax
.. _JsDoc:
.. _JsDoc Toolkit:
    http://code.google.com/p/jsdoc-toolkit/
.. _John Resig's Class implementation:
    http://ejohn.org/blog/simple-javascript-inheritance/
.. _\_.each:
    http://documentcloud.github.com/underscore/#each
.. _\_.map:
    http://documentcloud.github.com/underscore/#map
.. _\_.filter:
    http://documentcloud.github.com/underscore/#select
.. _It is also fairly tricky to use:
    https://developer.mozilla.org/en/JavaScript/Reference/Statements/for...in#Description
.. _Object.propertyIsEnumeable:
    https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Object/propertyIsEnumerable
.. _Object.defineProperty:
    https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Object/defineProperty
.. _Object.hasOwnProperty:
    https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Object/hasOwnProperty
