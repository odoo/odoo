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
written in plain english, using reStructuredText_ and taking advantage
of `Sphinx's extensions`_, especially `cross-references`_.

Python API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~

All public objects in Python code should have a docstring written in
RST, using Sphinx's `Python domain`_ [#]_:

* Functions and methods documentation should be in their own
  docstring, using Sphinx's `info fields`_

  For parameters types, built-in and stdlib types should be using the
  combined syntax::

      :param dict foo: what the purpose of foo is

  unless a more extensive explanation needs to be given (e.g. the
  specification that the input should be a list of 3-tuple needs to
  use ``:type:`` even though all types involved are built-ins). Any
  other type should be specified in full using the ``:type:`` field::

      :param foo: what the purpose of foo is
      :type foo: some.addon.Class

  Mentions of other methods (including within the same class), modules
  or types in descriptions (of anything, including parameters) should
  be cross-referenced.

* Classes should likewise be documented using their own docstring, and
  should include the documentation of their construction (``__init__``
  and ``__new__``), using the `info fields`_  as well.

* Attributes (class and instance) should be documented in their
  class's docstrin via the ``.. attribute::`` directiveg, following
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

  As a result, the bare minimum for a namespace is::

      /** @namespace */
      foo.bar.baz = {};

  while for a class it is::

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

.. [#] because Python is the default domain, the ``py:`` markup prefix
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
