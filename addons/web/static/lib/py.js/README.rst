What
====



Syntax
------

* Lambdas and ternaries should be parsed but are not implemented (in
  the evaluator)
* Only floats are implemented, ``int`` literals are parsed as floats.
* Octal and hexadecimal literals are not implemented
* Srings are backed by JavaScript strings and probably behave like
  ``unicode`` more than like ``str``
* Slices don't work

Builtins
--------

``py.js`` currently implements the following builtins:

``type``
    Restricted to creating new types, can't be used to get an object's
    type (yet)

``None``

``True``

``False``

``NotImplemented``
    Returned from rich comparison methods when the comparison is not
    implemented for this combination of operands. In ``py.js``, this
    is also the default implementation for all rich comparison methods.

``issubclass``

``object``

``bool``
    Does not inherit from ``int``, since ``int`` is not currently
    implemented.

``float``

``str``

``tuple``
    Constructor/coercer is not implemented, only handles literals

``list``
    Same as tuple (``list`` is currently an alias for ``tuple``)

``dict``
    Implements trivial getting and setting, nothing beyond that.

Note that most methods are probably missing from all of these.

Data model protocols
--------------------

``py.js`` currently implements the following protocols (or
sub-protocols) of the `Python 2.7 data model
<>`_:

Rich comparisons
    Pretty much complete (including operator fallbacks), although the
    behavior is currently undefined if an operation does not return
    either a ``py.bool`` or ``NotImplemented``.

    ``__hash__`` is supported (and used), but it should return **a
    javascript string**. ``py.js``'s dict build on javascript objects,
    reimplementing numeral hashing is worthless complexity at this
    point.

Boolean conversion
    Implementing ``__nonzero__`` should work.

Customizing attribute access
    Protocols for getting and setting attributes (including new-style
    extension) fully implemented but for ``__delattr__`` (since
    ``del`` is a statement)

Descriptor protocol
    As with attributes, ``__delete__`` is not implemented.

Callable objects
    Work, although the handling of arguments isn't exactly nailed
    down. For now, callables get two (javascript) arguments ``args``
    and ``kwargs``, holding (respectively) positional and keyword
    arguments.

    Conflicts are *not* handled at this point.

Collections Abstract Base Classes
    Container is the only implemented ABC protocol (ABCs themselves
    are not currently implemented) (well technically Callable and
    Hashable are kind-of implemented as well)

Numeric type emulation
    Operators are implemented (but not tested), ``abs``, ``divmod``
    and ``pow`` builtins are not implemented yet. Neither are ``oct``
    and ``hex`` but I'm not sure we care (I'm not sure we care about
    ``pow`` or even ``divmod`` either, for that matter)

Utilities
---------

``py.js`` also provides (and exposes) a few utilities for "userland"
implementation:

``def``
    Wraps a native javascript function into a ``py.js`` function, so
    that it can be called from native expressions.

    Does not ensure the return types are type-compatible with
    ``py.js`` types.

    When accessing instance methods, ``py.js`` automatically wraps
    these in a variant of ``py.def``, to behave as Python's (bound)
    methods.

Why
===

Originally, to learn about Pratt parsers (which are very, very good at
parsing expressions with lots of infix or mixfix symbols). The
evaluator part came because "why not" and because I work on a product
with the "feature" of transmitting Python expressions (over the wire)
which the client is supposed to evaluate.

How
===

At this point, only three steps exist in ``py.js``: tokenizing,
parsing and evaluation. It is possible that a compilation step be
added later (for performance reasons).

To evaluate a Python expression, the caller merely needs to call
`py.eval`_. `py.eval`_ takes a mandatory Python
expression to evaluate (as a string) and an optional context, for the
substitution of the free variables in the expression::

    > py.eval("type in ('a', 'b', 'c') and foo", {type: 'c', foo: true});
    true

This is great for one-shot evaluation of expressions. If the
expression will need to be repeatedly evaluated with the same
parameters, the various parsing and evaluation steps can be performed
separately: `py.eval`_ is really a shortcut for sequentially calling
`py.tokenize`_, `py.parse`_ and `py.evaluate`_.

API
===

.. _py.eval:

``py.eval(expr[, context])``
    "Do everything" function, to use for one-shot evaluation of a
    Python expression: it will internally handle the tokenizing,
    parsing and actual evaluation of the Python expression without
    having to perform these separately.

    ``expr``
        Python expression to evaluate
    ``context``
        context dictionary holding the substitutions for the free
        variables in the expression

.. _py.tokenize:

``py.tokenize(expr)``
    ``expr``
        Python expression to tokenize

.. _py.parse:

``py.parse(tokens)``
    Parses a token stream and returns an abstract syntax tree of the
    expression (if the token stream represents a valid Python
    expression).

    A parse tree is stateless and can be memoized and used multiple
    times in separate evaluations.

    ``tokens``
         stream of tokens returned by `py.tokenize`_

.. _py.evaluate:

``py.evaluate(ast[, context])``
    ``ast``
        The output of `py.parse`_
    ``context``
        The evaluation context for the Python expression.
