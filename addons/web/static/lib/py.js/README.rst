What
====

``py.js`` is a parser and evaluator of Python expressions, written in
pure javascript.

``py.js`` is not intended to implement a full Python interpreter
(although it could be used for such an effort later on), its
specification document is the `Python 2.7 Expressions spec
<http://docs.python.org/reference/expressions.html>`_ (along with the
lexical analysis part).

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
