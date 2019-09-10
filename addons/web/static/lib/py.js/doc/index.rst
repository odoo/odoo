.. py.js documentation master file, created by
   sphinx-quickstart on Sun Sep  9 19:36:23 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

py.js, a Python expressions parser and evaluator
================================================

``py.js`` is a parser and evaluator of Python expressions, written in
pure javascript.

``py.js`` is not intended to implement a full Python interpreter, its
specification document is the `Python 2.7 Expressions spec
<http://docs.python.org/reference/expressions.html>`_ (along with the
lexical analysis part) as well as the Python builtins.


.. toctree::
    :maxdepth: 2

    builtins
    types
    utility
    differences

Usage
-----

To evaluate a Python expression, simply call
:func:`py.eval`. :func:`py.eval` takes a mandatory Python expression
parameter, as a string, and an optional evaluation context (namespace
for the expression's free variables), and returns a javascript value::

    > py.eval("t in ('a', 'b', 'c') and foo", {t: 'c', foo: true});
    true

If the expression needs to be repeatedly evaluated, or the result of
the expression is needed in its "python" form without being converted
back to javascript, you can use the underlying triplet of functions
:func:`py.tokenize`, :func:`py.parse` and :func:`py.evaluate`
directly.

API
---

Core functions
++++++++++++++

.. function:: py.eval(expr[, context])

    "Do everything" function, to use for one-shot evaluation of Python
    expressions. Chains tokenizing, parsing and evaluating the
    expression then :ref:`converts the result back to javascript
    <convert-js>`

    :param expr: Python expression to evaluate
    :type expr: String
    :param context: evaluation context for the expression's free
                    variables
    :type context: Object
    :returns: the expression's result, converted back to javascript

.. function:: py.tokenize(expr)

    Expression tokenizer

    :param expr: Python expression to tokenize
    :type expr: String
    :returns: token stream

.. function:: py.parse(tokens)

    Parses a token stream and returns the corresponding parse tree.

    The parse tree is stateless and can be memoized and reused for
    frequently evaluated expressions.

    :param tokens: token stream from :func:`py.tokenize`
    :returns: parse tree

.. function:: py.evaluate(tree[, context])

    Evaluates the expression represented by the provided parse tree,
    using the provided context for the exprssion's free variables.

    :param tree: parse tree returned by :func:`py.parse`
    :param context: evaluation context
    :returns: the "python object" resulting from the expression's
              evaluation
    :rtype: :class:`py.object`

.. _convert-py:

Conversions from Javascript to Python
+++++++++++++++++++++++++++++++++++++

``py.js`` will automatically attempt to convert non-:class:`py.object`
values into their ``py.js`` equivalent in the following situations:

* Values passed through the context of :func:`py.eval` or
  :func:`py.evaluate`

* Attributes accessed directly on objects

* Values of mappings passed to :class:`py.dict`

Notably, ``py.js`` will *not* attempt an automatic conversion of
values returned by functions or methods, these must be
:class:`py.object` instances.

The automatic conversions performed by ``py.js`` are the following:

* ``null`` is converted to :data:`py.None`

* ``true`` is converted to :data:`py.True`

* ``false`` is converted to :data:`py.False`

* numbers are converted to :class:`py.float`

* strings are converted to :class:`py.str`

* functions are wrapped into :class:`py.PY_dev`

* ``Array`` instances are converted to :class:`py.list`

The rest generates an error, except for ``undefined`` which
specifically generates a ``NameError``.

.. _convert-js:

Conversions from Python to Javascript
+++++++++++++++++++++++++++++++++++++

py.js types (extensions of :js:class:`py.object`) can be converted
back to javascript by calling their :js:func:`py.object.toJSON`
method.

The default implementation raises an error, as arbitrary objects can
not be converted back to javascript.

Most built-in objects provide a :js:func:`py.object.toJSON`
implementation out of the box.

Javascript-level exceptions
+++++++++++++++++++++++++++

Javascript allows throwing arbitrary things, but runtimes don't seem
to provide any useful information (when they ever do) if what is
thrown isn't a direct instance of ``Error``. As a result, while
``py.js`` tries to match the exception-throwing semantics of Python it
only ever throws bare ``Error`` at the javascript-level. Instead, it
prefixes the error message with the name of the Python expression, a
colon, a space, and the actual message.

For instance, where Python would throw ``KeyError("'foo'")`` when
accessing an invalid key on a ``dict``, ``py.js`` will throw
``Error("KeyError: 'foo'")``.

.. _Python Data Model: http://docs.python.org/reference/datamodel.html

