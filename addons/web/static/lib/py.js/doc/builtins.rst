.. default-domain: python

.. _builtins:

Supported Python builtins
=========================

.. function:: py.type(object)

    Gets the class of a provided object, if possible.

    .. note:: currently doesn't work correctly when called on a class
              object, will return the class itself (also, classes
              don't currently have a type).

.. js:function:: py.type(name, bases, dict)

    Not exactly a builtin as this form is solely javascript-level
    (currently). Used to create new ``py.js`` types. See :doc:`types`
    for its usage.

.. data:: py.None

.. data:: py.True

.. data:: py.False

.. data:: py.NotImplemented

.. class:: py.object

    Base class for all types, even implicitly (if no bases are
    provided to :js:func:`py.type`)

.. class:: py.bool([object])

.. class:: py.float([object])

.. class:: py.str([object])

.. class:: py.unicode([object])

.. class:: py.tuple()

.. class:: py.list()

.. class:: py.dict()

.. function:: py.len(object)

.. function:: py.isinstance(object, type)

.. function:: py.issubclass(type, other_type)

.. class:: py.classmethod
