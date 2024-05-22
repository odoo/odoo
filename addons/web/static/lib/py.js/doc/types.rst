Implementing a custom type
==========================

To implement a custom python-level type, one can use the
:func:`py.type` builtin. At the JS-level, it is a function with the
same signature as the :py:class:`type` builtin [#bases]_. It returns a
child type of its one base (or :py:class:`py.object` if no base is
provided).

The ``dict`` parameter to :func:`py.type` can contain any
attribute, javascript-level or python-level: the default
``__getattribute__`` implementation will ensure they are converted to
Python-level attributes if needed. Most methods are also wrapped and
converted to :ref:`types-methods-python`, although there are a number
of special cases:

* Most "magic methods" of the data model ("dunder" methods) remain
  javascript-level. See :ref:`the listing of magic methods and their
  signatures <types-methods-dunder>`. As a result, they do not respect
  the :ref:`types-methods-python-call`

* The ``toJSON`` and ``fromJSON`` methods are special-cased to remain
  javascript-level and don't follow the
  :ref:`types-methods-python-call`

* Functions which have been wrapped explicitly (via
  :class:`py.PY_def`, :py:class:`py.classmethod` or
  :py:class:`py.staticmethod`) are associated to the class
  untouched. But due to their wrapper, they will use the
  :ref:`types-methods-python-call` anyway

.. _types-methods-python:

Python-level callable
---------------------

Wrapped javascript function *or* the :func:`__call__` method itself
follow the :ref:`types-methods-python-call`. As a result, they can't
(easily) be called directly from javascript code. Because
:func:`__new__` and :func:`__init__` follow from :func:`__call__`,
they also follow the :ref:`types-methods-python-call`.

:func:`py.PY_call` should be used when interacting with them from
javascript is necessary.

Because ``__call__`` follows the :ref:`types-methods-python-call`,
instantiating a ``py.js`` type from javascript requires using
:func:`py.PY_call`.

.. _types-methods-python-call:

Python calling conventions
++++++++++++++++++++++++++

The python-level arguments should be considered completely opaque,
they should be interacted with through :func:`py.PY_parseArgs` (to
extract python-level arguments to javascript implementation code) and
:func:`py.PY_call` (to call :ref:`types-methods-python` from
javascript code).

A callable following the :ref:`types-methods-python-call` *must*
return a ``py.js`` object, an error will be generated when failing to
do so.

.. todo:: arguments forwarding when e.g. overriding methods?

.. _types-methods-dunder:

Magic methods
-------------

``py.js`` doesn't support calling magic ("dunder") methods of the
datamodel from Python code, and these methods remain javascript-level
(they don't follow the :ref:`types-methods-python-call`).

Here is a list of the understood datamodel methods, refer to `the
relevant Python documentation
<http://docs.python.org/reference/datamodel.html?highlight=data%20model#special-method-names>`_
for their roles.

Basic customization
+++++++++++++++++++

.. function:: __hash__()

    :returns: String

.. function:: __eq__(other)

    The default implementation tests for identity

    :param other: :py:class:`py.object` to compare this object with
    :returns: :py:class:`py.bool`

.. function:: __ne__(other)

    The default implementation calls :func:`__eq__` and reverses
    its result.

    :param other: :py:class:`py.object` to compare this object with
    :returns: :py:class:`py.bool`

.. function:: __lt__(other)

    The default implementation simply returns
    :data:`py.NotImplemented`.

    :param other: :py:class:`py.object` to compare this object with
    :returns: :py:class:`py.bool`


.. function:: __le__(other)

    The default implementation simply returns
    :data:`py.NotImplemented`.

    :param other: :py:class:`py.object` to compare this object with
    :returns: :py:class:`py.bool`


.. function:: __ge__(other)

    The default implementation simply returns
    :data:`py.NotImplemented`.

    :param other: :py:class:`py.object` to compare this object with
    :returns: :py:class:`py.bool`


.. function:: __gt__(other)

    The default implementation simply returns
    :data:`py.NotImplemented`.

    :param other: :py:class:`py.object` to compare this object with
    :returns: :py:class:`py.bool`

.. function:: __str__()

    Simply calls :func:`__unicode__`. This method should not be
    overridden, :func:`__unicode__` should be overridden instead.

    :returns: :py:class:`py.str`

.. function:: __unicode__()

    :returns: :py:class:`py.unicode`

.. function:: __nonzero__()

    The default implementation always returns :data:`py.True`

    :returns: :py:class:`py.bool`

Customizing attribute access
++++++++++++++++++++++++++++

.. function:: __getattribute__(name)

    :param String name: name of the attribute, as a javascript string
    :returns: :py:class:`py.object`

.. function:: __getattr__(name)

    :param String name: name of the attribute, as a javascript string
    :returns: :py:class:`py.object`

.. function:: __setattr__(name, value)

    :param String name: name of the attribute, as a javascript string
    :param value: :py:class:`py.object`

Implementing descriptors
++++++++++++++++++++++++

.. function:: __get__(instance)

    .. note:: readable descriptors don't currently handle "owner
              classes"

    :param instance: :py:class:`py.object`
    :returns: :py:class:`py.object`

.. function:: __set__(instance, value)

    :param instance: :py:class:`py.object`
    :param value: :py:class:`py.object`

Emulating Numeric Types
+++++++++++++++++++++++

* Non-in-place binary numeric methods (e.g. ``__add__``, ``__mul__``,
  ...) should all be supported including reversed calls (in case the
  primary call is not available or returns
  :py:data:`py.NotImplemented`). They take a single
  :py:class:`py.object` parameter and return a single
  :py:class:`py.object` parameter.

* Unary operator numeric methods are all supported:

  .. function:: __pos__()

      :returns: :py:class:`py.object`

  .. function:: __neg__()

      :returns: :py:class:`py.object`

  .. function:: __invert__()

      :returns: :py:class:`py.object`

* For non-operator numeric methods, support is contingent on the
  corresponding :ref:`builtins <builtins>` being implemented

Emulating container types
+++++++++++++++++++++++++

.. function:: __len__()

    :returns: :py:class:`py.int`

.. function:: __getitem__(name)

    :param name: :py:class:`py.object`
    :returns: :py:class:`py.object`

.. function:: __setitem__(name, value)

    :param name: :py:class:`py.object`
    :param value: :py:class:`py.object`

.. function:: __iter__()

    :returns: :py:class:`py.object`

.. function:: __reversed__()

    :returns: :py:class:`py.object`

.. function:: __contains__(other)

    :param other: :py:class:`py.object`
    :returns: :py:class:`py.bool`

.. [#bases] with the limitation that, because :ref:`py.js builds its
            object model on top of javascript's
            <details-object-model>`, only one base is allowed.
