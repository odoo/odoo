:orphan:

==================================
Python 3 compatibility/conversions
==================================

Official compatibility: Odoo 11 will be the first LTS release to introduce
Python 3 compatibility, starting with Python 3.5. It will also be the first
LTS release to drop official support for Python 2.

Rationale: Python 3 has been around since 2008, and all Python libraries
used by the official Odoo distribution have been ported and are considered
stable. Most supported platforms have a Python 3.5 package, or a similar
way to deploy it. Preserving dual compatibility is therefore considered
unnecessary, and would represent a significant overhead in testing for the
lifetime of Odoo 11.

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
    generator delegation, pathlib, ...), you must *not* use them in Odoo
    until Python 2 support is dropped

.. note::

    In the *very rare* cases where you *need* to differentiate between
    Python 2 and Python 3, use the :data:`odoo.tools.pycompat.PY2` flag.

Semantics changes
=================

Dict & set iteration order ("Hash Randomisation")
-------------------------------------------------

In Python 2, the iteration order depends on the value's hash (modulo the
collection's capacity and conflict resolution), which provides a
spec-undefined but implementation-defined order. While that's not supposed to
happen, it turns out code may depend on the specific order of iteration over
a hash collection (``dict`` or ``set``).

Python 3.3 enables `hash randomisation`_ by default (this can be optionally
enabled on previous versions including Python 2 by providing the ``-R``
command-line parameter), which means *the order of iteration changes from one
run to the next*.

When discovered, this can be fixed by one of:

* making iteration steps properly independent (removing the dependency of
  order of iteration)
* using different checking method (e.g. when serialising sets or dictionaries
  and checking against the specific serialised value)
* fixing dependencies
* using a ``collections.OrderedDict`` or ``odoo.tools.misc.OrderedSet`` instead
  of a regular one, they guarantee order of iteration is order of insertion
* sorting the collection's items before iterating over them (this may require
  adding some sort of iteration key to the items)

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
      ``map`` or ``filter``.

* In Python 3, ``dict.keys``, ``dict.values`` and ``dict.items`` return
  *views* rather than lists, and the ``iter*`` and ``view*`` methods have
  been removed.

  .. important::

      When the result of the above methods is used for more than a one-shot
      loop (e.g. to be included in returned value), or when the dict needs
      to be modified during iteration, wrap the calls in a ``list()``.

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

In Python 3, ``range()`` behaves the same as Python 2's ``xrange``.

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

.. _changed-strings:

Bytes/String/Text: The Big One
==============================

The most impactful Python 3 change by far is to the text model: for historical
reasons the distinction Python 2's bytestrings (``bytes``/``str``) and text
strings (``unicode``) is fuzzy and it will try to implicitly convert between
one and the other using the ASCII encoding.

Python 3 changes this, it removes the implicit conversions, removes APIs which
contribute to the fuzz and tends to strictly segregate other to work on either
bytes or text.

This is fundamentally good and mostly sensible, but it means lots of breakage:

the builtins
------------

Python 3 removes both ``unicode`` and ``basestring``, and ``str`` now
corresponds to *text* strings (the old ``unicode``) with ``bytes`` being
bytestrings in both languages [#bytes]_.

Both versions have the following prefixes for string literals:

* ``b'foo'`` is a bytestring (``bytes`` object).

* ``'foo'`` is that version's ``str`` type, which may be either a bytestring
  or a text string [#native-string]_.

* ``u'foo'`` is that version's text string.

For best cross-version compatibility you should avoid unprefixed string
literals unless you *specifically* need a "native string" [#native-string]_.

For easier type-testing, :mod:`odoo.tools.pycompat` provides the following
constants:

* :data:`~odoo.tools.pycompat.string_types` is an alias/type tuple for testing
  string types, essentially a replacement of testing for ``basestring`` or
  ``(str, unicode)``.
* :data:`~odoo.tools.pycompat.text_type` is the proper *text* type for the
  current version, it should mostly be used for converting non-bytes objects
  to text.
* ``bytes`` should be avoided for type conversions, though it can be used to
  check if an object is a bytestring.

``open``
--------

.. important::

    the ``open`` builtin should always be explicitly used in binary mode
    (``rb``, ``wb``, ...)

    To read *text* files, use ``io.open``.

On both P2 and P3, ``open`` defaults to returning *native strings* in default
("text") mode, however in P3 that means it actually decodes the file's bytes
using whatever encoding was set up (default: UTF-8) while on Python 2 it has
no concept of encoding.

Using ``open`` in binary mode provides bytestrings on both versions and works
fine. To read *text* files, use ``io.open`` and provide an explicit encoding.

base64
------

base64 is a bytes->bytes conversion. bytes->bytes codecs were removed from the
"native" encoding/decoding system which is now exclusively for bytes<->text
conversions: text is *encoded* to bytes and bytes are *decoded* to text.

.. important::

    both ``bytes.encode('base64')`` and ``bytes.decode('base64')`` must be
    migrated to using ``base64.b64encode`` and ``base64.b64decode``
    respectively.

csv
---

``csv`` is a fairly vicious one: not only is it not a very good format, the
Python 2 and Python 3 versions of the library are text-model incompatible in
significant ways:

* Python 2's CSV only works on *ascii-compatible byte streams* (it has no
  encoding support at all) and extracts bytestring values
* Python 3's CSV only works on *text streams* and extract text values
* And ``io`` doesn't provide "native string" streaming facilities.

However with respect to Odoo it turns out most or all uses of ``csv`` fit
inside a model of *byte stream to and from text values*.

The latter is thus a model implemented by cross-version wrappers
:func:`odoo.tools.pycompat.csv_reader` and
:func:`odoo.tools.pycompat.csv_writer`: they take a *UTF-8 byte stream* and
read or write *text* values.

.. _hash randomisation: http://bugs.python.org/issue13703

.. _requests: http://docs.python-requests.org/

.. _werkzeug: http://werkzeug.pocoo.org/docs/urls/

.. [#bytes]

    with the caveat that Python 3 makes them less text-y and more byte-y e.g.
    in Python 2 ``b"foo"[0]`` is ``b"f"``, but in Python 3 it's ``102`` (the
    value of the first byte), you'll want to *slice* bytestrings for
    compatibility.

.. [#native-string]

    this is important because some API/contexts take a *native string* rather
    than either bytes or text. The ``csv`` module of the standard library is
    one such problematic API (it is also notoriously problematic for its
    terrible support of non-ascii-compatible encodings in Python 2).
    ``email.message_from_string`` is an other one.
