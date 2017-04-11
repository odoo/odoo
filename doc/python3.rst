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

References/useful documents:

* `How do I port to Python 3? <https://eev.ee/blog/2016/07/31/python-faq-how-do-i-port-to-python-3/>`_
* `Python-Future <http://python-future.org/index.html>`_
* `Porting Python 2 code to Python 3 <https://docs.python.org/3/howto/pyporting.html>`_
* `Porting to Python 3: A Guide <http://lucumr.pocoo.org/2010/2/11/porting-to-python-3-a-guide/>`_ (a bit outdated but useful for the extensive comments on strings and IO)

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
* Python 3.2 made ``range`` views more list-like and reintroduced ``callable``

.. warning::

    Python 3 adds plenty of great features (keyword-only parameters,
    generator delegation, pathlib, ...), do not use them until Python 2
    support is dropped

Fixes
=====

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

Removed Operators
-----------------

.. important::

    * The backtick operator ``\`foo\``` must be converted to an explicit call
      to the ``repr()`` builtin
    * The ``<>`` operator must be replaced by ``!=``

These two operators were long recommended against/deprecated in Python 2,
Python 3 removed them from the language.

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
