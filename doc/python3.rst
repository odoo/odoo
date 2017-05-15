:orphan:

==================================
Python 3 compatibility/conversions
==================================

Goal (notsure?): for v11 to provide an alpha/beta Python 3 compatibility, for
v12 to provide official Python 3 support and drop Python 2 in either v12 or
v13.

Python 2 and Python 3 are somewhat different language, but following
backports, forward ports and cross-compatibility library it is possible to
use a subset of Python 2 and Python 3 in order to have a system compatible
with both.

Here are a few useful steps or reminders to make Python 2 code compatible
with Python 3.

.. important::

    This is not a general-purpose guide for porting Python 2 to Python 3, it's
    a guide to write 2/3-compatible Odoo code. It does not go through all the
    changes in Python but rather through issues which have been found in the
    standard Odoo distribution in order to show how to evolve such code such
    that it works on both Python 2 and Python 3.

References/useful documents:

* `What's new in Python 3? <https://docs.python.org/3.0/whatsnew/3.0.html>`_
  covers many of the changes between Python 2 and Python 3, though it is
  missing a number of changes which `were backported to Python 2.7 <https://docs.python.org/2.7/whatsnew/2.7.html#python-3-1-features>`_
  as well as :ref:`some feature reintroductions <p3support>` of later Python 3
  revisions
* `How do I port to Python 3? <https://eev.ee/blog/2016/07/31/python-faq-how-do-i-port-to-python-3/>`_
* `Python-Future <http://python-future.org/index.html>`_
* `Porting Python 2 code to Python 3 <https://docs.python.org/3/howto/pyporting.html>`_
* `Porting to Python 3: A Guide <http://lucumr.pocoo.org/2010/2/11/porting-to-python-3-a-guide/>`_ (a bit outdated but useful for the extensive comments on strings and IO)

.. _p3support:

Versions Support
================

A cross compatible Odoo would only support Python 2.7 and Python 3.5 and
above: Python 2.7 backported some Python 3 features, and Python 2 features
were reintroduced in various Python 3 in order to make conversion easier.
Python 3.6 adds great features (f-strings, ...) and performance improvements
(ordered compact dicts) but does not seem to reintroduce compatibility
features whereas:

* Python 3.5 reintroduced ``%`` for bytes/bytestrings (:pep:`461`)
* Python 3.4 has no specific compatibility improvement but is the lowest P3
  version for PyLint
* Python 3.3 reintroduced the "u" prefix for proper (unicode) strings
* Python 3.2 made ``range`` views more list-like (backported to 2.7)and
  reintroduced ``callable``

.. warning::

    While Python 3 adds plenty of great features (keyword-only parameters,
    generator delegation, pathlib, ...), you must *not *use them in Odoo
    until Python 2 support is dropped

Moved and removed
=================

Standard Library Modules
------------------------

Python 3 reorganised, moved or removed a number of modules in the standard
library:

* ``StringIO`` and ``cStringIO`` were removed, you can use ``io.BytesIO`` and
  ``io.StringIO`` to replace them in a cross-version manner (``io.BytesIO``
  for binary data, ``io.StringIO`` for text/unicode data).
* ``urllib``, ``urllib2`` and ``urlparse`` were redistributed across
  ``urllib.parse`` and ``urllib.request``.

  Since `requests`_ and `werkzeug`_ are already hard dependencies of Odoo,
  replace ``urllib[2].urlopen``/``urllib2.Request`` uses by `requests`_, and
  ``urlparse`` and a few utilty functions (``urllib.quote``,
  ``urllib.urlencode``) are available through ``werkzeug.urls``, a backport
  of Python 3's ``urllib.parse``.

  .. warning:: `requests`_ does not raise by default on non-200 responses

* ``cgi.escape`` (HTML escaping) is deprecated in Python 3, prefer Odoo's own
  :func:`odoo.tools.misc.html_encode`.
* Most of ``types``'s content has been stripped out in Python 3: only
  "internal" interpreter types (e.g. CodeType, FrameType, ...) have been left
  in, other types can be obtained directly from the corresponding builtin or
  by getting the ``type()`` of a literal value.

Absolute Imports (:pep:`328`)
-----------------------------

.. important::

    In Python 3, ``import foo`` can only import from a "top-level" library
    (absolute path). If trying to import a sibling or sub-module you *must*
    use an explicitly *relative import* e.g. ``from . import foo`` or
    ``from .foo import bar``.

In Python 2 ``import`` statements are ambiguous: if a file ``a.py`` contains
``import b``, the import system will first check if there's a ``b.py`` file
next to it before checking if there is a package called that on the
PYTHONPATH.

Furthermore if a sibling file is named the same as top-level package, the
library becomes inaccessible to both the file itself ans siblings, this has
actually happened in Odoo with :mod:`odoo.tools.mimetypes`.

Additionally, relative imports allow navigating "up" the tree by using
multiple leading ``.``.

.. note::

    Explicitly relative imports are always available in Python 2, and should
    be used everywhere.

    You can ensure you are not using any implicitly relative import by adding
    ``from __future__ import absolute_import`` at the top of your files, or by
    running the ``relative-import`` PyLint.

Exception Handlers
------------------

.. important::

    All exception handlers must be converted to ``except ... as ..``. Valid
    forms are::

        except Exception:
        except (Exception1, ...):
        except Exception as name:
        except (Exception1, ...) as name:

In Python 2, ``except`` statements are of the form::

    except Exception[, name]:

or::

    except (Exception1, Exception2)[, name]:

But because the name is optional, this gets confusing and people can stumble
into the first form when trying for the second and write::

    except Exception1, Exception:

which will *not* yield the expected result.

Python 3 changes this syntax to::

    except Exception[ as name]:

or::

    except (Exception1, Exception2)[ as name]:

This form was implemented in Python 2.5 and is thus compatible across the
board.

Operators & keywords
--------------------

.. important:: The backtick operator ```foo``` must be converted to an
               explicit call to the ``repr()`` builtin

.. important:: The ``<>`` operator must be replaced by ``!=``

These two operators were long recommended against/deprecated in Python 2,
Python 3 removed them from the language.

.. _changed-exec:

.. important:: ``exec`` is now a builtin

In Python 2, ``exec`` is a statement/keyword. Much like ``print``, it's been
converted to a builtin function in Python 3. However because the Python 2
version can take a tuple parameter it is easy to convert the odd ``exec``
statement to the following cross-language forms::

    exec(source)
    exec(source, globals)
    exec(source, globals, locals)

List/iteration builtins and methods
-----------------------------------

In Python 3, a number of builtins and methods formerly returning *lists* were
converted to return *iterators* or *views*, with the corresponding redundant
methods or functions having been *removed entirely*:

* In Python 3, ``map``, ``filter`` and ``zip`` return iterators,
  ``itertools.imap``, ``itertools.ifilter`` and ``itertools.izip`` have been
  removed.

  .. important::

      When possible, use comprehensions (list, generator, ...) rather than
      ``map`` or ``filter``, otherwise use the cross-version ``pycompat``
      versions (``pycompat.imap``, ``pycompat.ifilter`` and
      ``pycompat.izip``). The ``pycompat`` versions all return *iterators* and
      may need to be wrapped in a ``list()`` call to yield a list.

* In Python 3, ``dict.keys``, ``dict.values`` and ``dict.items`` return
  *views* rather than lists, and the ``iter*`` and ``view*`` methods have
  been removed.

  .. important::

      Prefer using :func:`odoo.tools.pycompat.keys`,
      :func:`odoo.tools.pycompat.values` and :func:`odoo.tools.pycompat.items`
      return cross-version iterators. When needing actual lists (e.g. to
      modify a dictionary during iteration), wrap one of the calls above in a
      ``list()``.

builtins
--------

``cmp``
#######

The ``cmp`` builtin function has been removed from Python 3.

* Most of its uses are in ``cmp=`` parameters to sort functions where it can
  usually be replaced by a key function.
* Other uses found were obtaining the sign of an item (``cmp(item, 0)``), this
  can be replicated using the standard library's ``math.copysign`` e.g.
  ``math.copysign(1, item)`` will return ``1.0`` if ``item`` is positive and
  ``-1.0`` if ``item`` is negative.

``execfile``
############

``execfile(path)`` has been removed completely from Python 3 but it is
trivially replaceable in all cases by::

    exec(open(path, 'rb').open())

of a variant thereof (see :ref:`exec changes <changed-exec>` for details)

``file``
########

The ``file`` builtin has been removed in Python 3. Generally, it can just
be replaced by the ``open`` builtin, although you may want to use ``io.open``
which is more flexible and better handles the binary/text dichotomy,
:ref:`a big issue in cross-version Python <changed-strings>`.

.. note::

    In Python 3, the ``open`` builtin is actually an alias for ``io.open``.

``long``
########

In Python 2, integers can be either ``int`` or ``long``. Python 3 unifies this
under the single ``int`` type.

.. important::

    * the ``L`` suffix for integer literals must be removed
    * calls to ``long`` must be replaced by calls to ``int``
    * ``(int, long)`` for type-checking purposes must be replaced by
      :py:data:`odoo.tools.pycompat.integer_types`


* the ``L`` suffix on numbers is unsupported in Python 3, and unnecessary in
  Python 2 as "overflowing" integer literals will implicitly instantiate long.
* in Python 2, a call to ``int()`` will implicitly create a ``long`` object if
  necessary.
* type-testing is the last and bigger issue as in Python 2 ``long`` is not a
  subtype of ``int`` (nor the reverse), and ``isinstance(value, (int, long))``
  is thus generally necessary to catch all integrals.

  For that case, Odoo 11 now provides a compatibility module with an
  :py:data:`~odoo.tools.pycompat.integer_types` definition which can be used
  for type-testing.

  It is a tuple of types so when used with ``isinstance`` it can be provided
  directly or inside an other tuple alongside other types e.g.
  ``isinstance(value, (BaseModel, integer_types))``.

  However when used with ``type`` directly (which should be avoided) you
  should use the ``in`` operator, and if you need other types you need to
  concatenate ``integer_types`` to an other tuple.

``reduce``
##########

In Python 3, ``reduce`` has been demoted from builtin to ``functools.reduce``.
However this is because *most uses of ``reduce`` can be replaced by ``sum``,
``all``, ``any``* or a list comprehension for a more readable and faster
result.

It is easy enough to just add ``from functools import reduce`` to the file
and compatible with Python 2.6 and later, but consider whether you get better
code by replacing it with some other method altogether.

``xrange``
##########

In Python 3, ``range()`` behaves the same as Python 3's ``xrange``.

For cross-version code, you can just use ``range()`` everywhere: while this
will incur a slight allocation cost on Python 2, Python 3's ``range`` supports
the entire Sequence protocol and thus behaves very much like a regular
list or tuple.

Removed/renamed methods
-----------------------

.. important::

    * the ``has_key`` method on dicts must be replaced by use of the ``in``
      operator e.g. ``foo.has_key(bar)`` becomes ``bar in foo``.

``in`` for dicts was introduced in Python 2.3, leading to ``has_key`` being
redundant, and removed in Python 3.

Minor syntax changes
--------------------

* the ability to unpack a parameter (in the parameter declaration list) has
  been removed in Python 3 e.g.::

      def foo((bar, baz), qux):
          …

  is now invalid

* octal literals must be prefixed by ``0o`` (or ``0O``). Following the C
  family, in Python 2 an octal literal simply has a leading 0, which can be
  confusing and easy to get wrong when e.g. padding for readability (e.g.
  ``0013`` would be the decimal 11 rather than 13).

  In Python 3, leading zeroes followed by neither a 0 nor a period is an
  error, octal literals now follow the hexadecimal convention with a ``0o``
  prefix.

.. _requests: http://docs.python-requests.org/

.. _werkzeug: http://werkzeug.pocoo.org/docs/urls/
