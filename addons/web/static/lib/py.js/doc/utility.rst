Utility functions for interacting with ``py.js`` objects
========================================================

Essentially the ``py.js`` version of the Python C API, these functions
are used to implement new ``py.js`` types or to interact with existing
ones.

They are prefixed with ``PY_``.

.. function:: py.PY_call(callable[, args][, kwargs])

    Call an arbitrary python-level callable from javascript.

    :param callable: A ``py.js`` callable object (broadly speaking,
                     either a class or an object with a ``__call__``
                     method)

    :param args: javascript Array of :class:`py.object`, used as
                 positional arguments to ``callable``

    :param kwargs: javascript Object mapping names to
                   :class:`py.object`, used as named arguments to
                   ``callable``

    :returns: nothing or :class:`py.object`

.. function:: py.PY_parseArgs(arguments, format)

    Arguments parser converting from the :ref:`user-defined calling
    conventions <types-methods-python-call>` to a JS object mapping
    argument names to values. It serves the same role as
    `PyArg_ParseTupleAndKeywords`_.

    ::

        var args = py.PY_parseArgs(
            arguments, ['foo', 'bar', ['baz', 3], ['qux', "foo"]]);

    roughly corresponds to the argument spec:

    .. code-block:: python

        def func(foo, bar, baz=3, qux="foo"):
            pass

    .. note:: a significant difference is that "default values" will
              be re-evaluated at each call, since they are within the
              function.

    :param arguments: array-like objects holding the args and kwargs
                      passed to the callable, generally the
                      ``arguments`` of the caller.

    :param format: mapping declaration to the actual arguments of the
                   function. A javascript array composed of five
                   possible types of elements:

                   * The literal string ``'*'`` marks all following
                     parameters as keyword-only, regardless of them
                     having a default value or not [#kwonly]_. Can
                     only be present once in the parameters list.

                   * A string prefixed by ``*``, marks the positional
                     variadic parameter for the function: gathers all
                     provided positional arguments left and makes all
                     following parameters keyword-only
                     [#star-args]_. ``*args`` is incompatible with
                     ``*``.

                   * A string prefixed with ``**``, marks the
                     positional keyword variadic parameter for the
                     function: gathers all provided keyword arguments
                     left and closes the argslist. If present, this
                     must be the last parameter of the format list.

                   * A string defines a required parameter, accessible
                     positionally or through keyword

                   * A pair of ``[String, py.object]`` defines an
                     optional parameter and its default value.

                   For simplicity, when not using optional parameters
                   it is possible to use a simple string as the format
                   (using space-separated elements). The string will
                   be split on whitespace and processed as a normal
                   format array.

    :returns: a javascript object mapping argument names to values

    :raises: ``TypeError`` if the provided arguments don't match the
             format

.. class:: py.PY_def(fn)

    Type wrapping javascript functions into py.js callables. The
    wrapped function follows :ref:`the py.js calling conventions
    <types-methods-python-call>`

    :param Function fn: the javascript function to wrap
    :returns: a callable py.js object

.. [#kwonly] Python 2, which py.js currently implements, does not
             support Python-level keyword-only parameters (it can be
             done through the C-API), but it seemed neat and easy
             enough so there.

.. [#star-args] due to this and contrary to Python 2, py.js allows
                arguments other than ``**kwargs`` to follow ``*args``.

.. _PyArg_ParseTupleAndKeywords:
    http://docs.python.org/c-api/arg.html#PyArg_ParseTupleAndKeywords
