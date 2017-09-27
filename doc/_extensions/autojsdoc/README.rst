:orphan:

======================================
JSDoc parser/Sphinx extension for Odoo
======================================

Why?
====

Spent about a week trying to coerce "standard" javascript tools (jsdoc_ with
the hope of using sphinx-js_ for integration or `documentation.js`_) and
failed to ever get a sensible result: failed to get any result with the
current state of the documentation, significant changes/additions/fixes to
docstrings brought this up to "garbage output" level.

Bug reports and mailing list posts didn't show any path to improvement on the
ES5 codebase (if we ever go whole-hog on ES6 modules and classes things could
be different, in fact most of JSDoc's current effort seem focused on
ES6/ES2015 features) but both experience and looking at the mailing lists
told me that spending more time would be wasted.

Even more so as I was writing visitors/rewriters to generate documentation
from our existing structure, which broadly speaking is relatively strict, and
thus

What?
=====

If it were possible to generate JSDoc annotations from our relatively
well-defined code structures, it was obviously possible to extract documentary
information directly from it, hence this Odoo-specific package/extension
trying to do exactly that.

This package should eventually provide:

* a command-line interface which can be invoked via ``-m autojsdoc`` (assuming
  your ``PYTHONPATH`` can find it) which should allow dumping the parsed AST
  in a convenient-ish form, possibly doing searches through the AST, a
  dependency graph extractor/analysis and a text dumper for the
  documentation.

* a sphinx extension (``autojsdoc.sphinx``) which can be used to integrate the
  parsed JSDoc information into the Sphinx doc.

How?
====

Sphinx-aside, the package relies on 3 libraries:

* pyjsparser_, an Esprima-compliant ES5.1 parser (with bits of ES6 support),
  sadly it does not support comments in its current form so I had to fork it.
  Fed a javascript source file, pyjsparser_ simply generates a bunch of nested
  dicts representing an Esprima ast, ast-types_ does a reasonably good job of
  describing it once you understand that "bases" are basically just structural
  mixins.

  Because the original does not, this package provides a ``visitor`` module
  for pyjsparser_ ASTs.

* pyjsdoc_, a one-file "port" of jsdoc, can actually do much of the JS parsing
  (using string munging) but its core semantics don't fit our needs so I'm
  only using it to parse the actual JSDoc content, and the ``jsdoc`` module
  contains some replacement classes, extensions & monkey patches for things
  `pyjsdoc`_ itself does not support, at the time of this writing:

  - a bug in FunctionDoc.return_val
  - a type on FunctionDoc so it's compatible with ParamDoc
  - a more reliable comments-parsing function
  - a replacement ModuleDoc as the original does not materialise AMD modules
  - a ClassDoc extension to support mixins
  - two additional CommentDoc extensions for "namespaces" objects (bag of
    attributes without any more information) and mixin objects

* pytest_ to configure and run the test suite, which you can run by invoking
  ``pytest doc/_extensions`` from the project top-level, the tests represent
  both "happy path" things we want to parse and various code patterns which
  tripped the happy path because e.g. they were matched and should not have,
  they were not matched and should have, or they were more complex than the
  happy path had expected

.. _ast-types: _https://github.com/benjamn/ast-types/blob/master/def/core.js
.. _documentation.js: http://documentation.js.org
.. _jsdoc: http://usejsdoc.org
.. _pyjsdoc: https://github.com/nostrademons/pyjsdoc
.. _pyjsparser: https://github.com/PiotrDabkowski/pyjsparser
.. _pytest: https://pytest.org/
.. _sphinx-js: https://sphinx-js-howto.readthedocs.io
