Utility functions for interacting with ``py.js`` objects
========================================================

Essentially the ``py.js`` version of the Python C API, these functions
are used to implement new ``py.js`` types or to interact with existing
ones.

They are prefixed with ``PY_``.

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

Object Protocol
---------------

.. function:: py.PY_hasAttr(o, attr_name)

    Returns ``true`` if ``o`` has the attribute ``attr_name``,
    otherwise returns ``false``. Equivalent to Python's ``hasattr(o,
    attr_name)``

    :param o: A :class:`py.object`
    :param attr_name: a javascript ``String``
    :rtype: ``Boolean``

.. function:: py.PY_getAttr(o, attr_name)

    Retrieve an attribute ``attr_name`` from the object ``o``. Returns
    the attribute value on success, raises ``AttributeError`` on
    failure. Equivalent to the python expression ``o.attr_name``.

    :param o: A :class:`py.object`
    :param attr_name: a javascript ``String``
    :returns: A :class:`py.object`
    :raises: ``AttributeError``

.. function:: py.PY_str(o)

    Computes a string representation of ``o``, returns the string
    representation. Equivalent to ``str(o)``

    :param o: A :class:`py.object`
    :returns: :class:`py.str`

.. function:: py.PY_isInstance(inst, cls)

    Returns ``true`` if ``inst`` is an instance of ``cls``, ``false``
    otherwise.

.. function:: py.PY_isSubclass(derived, cls)

    Returns ``true`` if ``derived`` is ``cls`` or a subclass thereof.

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

.. function:: py.PY_isTrue(o)

    Returns ``true`` if the object is considered truthy, ``false``
    otherwise. Equivalent to ``bool(o)``.

    :param o: A :class:`py.object`
    :rtype: Boolean

.. function:: py.PY_not(o)

    Inverse of :func:`py.PY_isTrue`.

.. function:: py.PY_size(o)

    If ``o`` is a sequence or mapping, returns its length. Otherwise,
    raises ``TypeError``.

    :param o: A :class:`py.object`
    :returns: ``Number``
    :raises: ``TypeError`` if the object doesn't have a length

.. function:: py.PY_getItem(o, key)

    Returns the element of ``o`` corresponding to the object
    ``key``. This is equivalent to ``o[key]``.

    :param o: :class:`py.object`
    :param key: :class:`py.object`
    :returns: :class:`py.object`
    :raises: ``TypeError`` if ``o`` does not support the operation, if
             ``key`` or the return value is not a :class:`py.object`

.. function:: py.PY_setItem(o, key, v)

    Maps the object ``key`` to the value ``v`` in ``o``. Equivalent to
    ``o[key] = v``.

    :param o: :class:`py.object`
    :param key: :class:`py.object`
    :param v: :class:`py.object`
    :raises: ``TypeError`` if ``o`` does not support the operation, or
             if ``key`` or ``v`` are not :class:`py.object`

Number Protocol
---------------

.. function:: py.PY_add(o1, o2)

    Returns the result of adding ``o1`` and ``o2``, equivalent to
    ``o1 + o2``.

    :param o1: :class:`py.object`
    :param o2: :class:`py.object`
    :returns: :class:`py.object`

.. function:: py.PY_subtract(o1, o2)

    Returns the result of subtracting ``o2`` from ``o1``, equivalent
    to ``o1 - o2``.

    :param o1: :class:`py.object`
    :param o2: :class:`py.object`
    :returns: :class:`py.object`

.. function:: py.PY_multiply(o1, o2)

    Returns the result of multiplying ``o1`` by ``o2``, equivalent to
    ``o1 * o2``.

    :param o1: :class:`py.object`
    :param o2: :class:`py.object`
    :returns: :class:`py.object`

.. function:: py.PY_divide(o1, o2)

    Returns the result of dividing ``o1`` by ``o2``, equivalent to
    ``o1 / o2``.

    :param o1: :class:`py.object`
    :param o2: :class:`py.object`
    :returns: :class:`py.object`

.. function:: py.PY_negative(o)

    Returns the negation of ``o``, equivalent to ``-o``.

    :param o: :class:`py.object`
    :returns: :class:`py.object`

.. function:: py.PY_positive(o)

    Returns the "positive" of ``o``, equivalent to ``+o``.

    :param o: :class:`py.object`
    :returns: :class:`py.object`

.. [#kwonly] Python 2, which py.js currently implements, does not
             support Python-level keyword-only parameters (it can be
             done through the C-API), but it seemed neat and easy
             enough so there.

.. [#star-args] due to this and contrary to Python 2, py.js allows
                arguments other than ``**kwargs`` to follow ``*args``.

.. _PyArg_ParseTupleAndKeywords:
    http://docs.python.org/c-api/arg.html#PyArg_ParseTupleAndKeywords
