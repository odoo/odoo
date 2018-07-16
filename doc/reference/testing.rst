:banner: banners/testing_modules.jpg

.. _reference/testing:


===============
Testing Odoo
===============

There are many ways to test an application.  In Odoo, we have three kinds of
tests

- python unit tests: useful for testing model business logic
- js unit tests: this is necessary to test the javascript code in isolation
- tours: this is a form of integration testing.  The tours ensure that the
  python and the javascript parts properly talk to each other.

Testing Python code
===================

Odoo provides support for testing modules using unittest.

To write tests, simply define a ``tests`` sub-package in your module, it will
be automatically inspected for test modules. Test modules should have a name
starting with ``test_`` and should be imported from ``tests/__init__.py``,
e.g.

.. code-block:: text

    your_module
    |-- ...
    `-- tests
        |-- __init__.py
        |-- test_bar.py
        `-- test_foo.py

and ``__init__.py`` contains::

    from . import test_foo, test_bar

.. warning::

    test modules which are not imported from ``tests/__init__.py`` will not be
    run

.. versionchanged:: 8.0

    previously, the test runner would only run modules added to two lists
    ``fast_suite`` and ``checks`` in ``tests/__init__.py``. In 8.0 it will
    run all imported modules

The test runner will simply run any test case, as described in the official
`unittest documentation`_, but Odoo provides a number of utilities and helpers
related to testing Odoo content (modules, mainly):

.. autoclass:: odoo.tests.common.TransactionCase
    :members: browse_ref, ref

.. autoclass:: odoo.tests.common.SingleTransactionCase
    :members: browse_ref, ref

.. autoclass:: odoo.tests.common.SavepointCase

.. autoclass:: odoo.tests.common.HttpCase
    :members: browse_ref, ref, url_open, phantom_js

.. autofunction:: odoo.tests.common.tagged

By default, tests are run once right after the corresponding module has been
installed. Test cases can also be configured to run after all modules have
been installed, and not run right after the module installation:

.. autofunction:: odoo.tests.common.at_install

.. autofunction:: odoo.tests.common.post_install

The most common situation is to use
:class:`~odoo.tests.common.TransactionCase` and test a property of a model
in each method::

    class TestModelA(common.TransactionCase):
        def test_some_action(self):
            record = self.env['model.a'].create({'field': 'value'})
            record.some_action()
            self.assertEqual(
                record.field,
                expected_field_value)

        # other tests...

.. note::

    Test methods must start with ``test_``

.. autoclass:: odoo.tests.common.Form
    :members:

.. autoclass:: odoo.tests.common.M2MProxy
    :members: add, remove, clear

.. autoclass:: odoo.tests.common.O2MProxy
    :members: new, edit, remove

Running tests
-------------

Tests are automatically run when installing or updating modules if
:option:`--test-enable <odoo-bin --test-enable>` was enabled when starting the
Odoo server.

As of Odoo 8, running tests outside of the install/update cycle is not
supported.

.. _unittest documentation: https://docs.python.org/2/library/unittest.html

Test selection
--------------

In Odoo, Python tests can be tagged to facilitate the test selection when
running tests.

Subclasses of :class:`odoo.tests.common.BaseCase` (usually through
:class:`~odoo.tests.common.TransactionCase`,
:class:`~odoo.tests.common.SavepointCase` or
:class:`~odoo.tests.common.HttpCase`) are automatically tagged with
``standard``, ``at_install`` and their source module's name by default.

Invocation
^^^^^^^^^^

:option:`--test-tags <odoo-bin --test-tags>` can be used to select/filter tests
to run on the command-line.

This option defaults to ``+standard`` meaning tests tagged ``standard``
(explicitly or implicitly) will be run by default when starting Odoo
with :option:`--test-enable <odoo-bin --test-enable>`.

When writing tests, the :func:`~odoo.tests.common.tagged` decorator can be
used on **test classes** to add or remove tags.

The decorator's arguments are tag names, as strings.

.. danger:: :func:`~odoo.tests.common.tagged` is a class decorator, it has no
            effect on functions or methods

Tags can be prefixed with the minus (``-``) sign, to *remove* them instead of
add or select them e.g. if you don't want your test to be executed by
default you can remove the ``standard`` tag:

.. code-block:: python

    from odoo.tests import TransactionCase, tagged

    @tagged('-standard', 'nice')
    class NiceTest(TransactionCase):
        ...

This test will not be selected by default, to run it the relevant tag will
have to be selected explicitely:

.. code-block:: console

    $ odoo-bin --test-enable --test-tags nice

Note that only the tests tagged ``nice`` are going to be executed. To run
*both* ``nice`` and ``standard`` tests, provide multiple values to
:option:`--test-tags <odoo-bin --test-tags>`: on the command-line, values
are *additive* (you're selecting all tests with *any* of the specified tags)

.. code-block:: console

    $ odoo-bin --test-enable --test-tags nice,standard

The config switch parameter also accepts the ``+`` and ``-`` prefixes. The
``+`` prefix is implied and therefore, totaly optional. The ``-`` (minus)
prefix is made to deselect tests tagged with the prefixed tags, even if they
are selected by other specified tags e.g. if there are ``standard`` tests which
are also tagged as ``slow`` you can run all standard tests *except* the slow
ones:

.. code-block:: console

    $ odoo-bin --test-enable --test-tags 'standard,-slow'

When you write a test that does not inherit from the
:class:`~odoo.tests.common.BaseCase`, this test will not have the default tags,
you have to add them explicitely to have the test included in the default test
suite.  This is a common issue when using a simple ``unittest.TestCase`` as
they're not going to get run:

.. code-block:: python

    import unittest
    from odoo.tests import tagged

    @tagged('standard', 'at_install')
    class SmallTest(unittest.TestCase):
        ...

Special tags
^^^^^^^^^^^^

- ``standard``: All Odoo tests that inherit from
  :class:`~odoo.tests.common.BaseCase` are implicitely tagged standard.
  :option:`--test-tags <odoo-bin --test-tags>` also defaults to ``standard``.

  That means untagged test will be executed by default when tests are enabled.
- ``at_install``: Means that the test will be executed right after the module
  installation and before other modules are installed. This is a default
  implicit tag.
- ``post_install``: Means that the test will be executed after all the modules
  are installed. This is what you want for HttpCase tests most of the time.

  Note that this is *not exclusive* with ``at_install``, however since you
  will generally not want both ``post_install`` is usually paired with
  ``-at_install`` when tagging a test class.
- *module_name*: Odoo tests classes extending
  :class:`~odoo.tests.common.BaseCase` are implicitely tagged with the
  technical name of their module. This allows easily selecting or excluding
  specific modules when testing e.g. if you want to only run tests from
  ``stock_account``:

  .. code-block:: console

      $ odoo-bin --test-enable --test-tags stock_account

Examples
^^^^^^^^

.. important::

    Tests will be executed only in the installed or updated modules.  So
    modules have to be selected with the :option:`-u <odoo-bin -u>` or
    :option:`-i <odoo-bin -i>` switches.  For simplicity, those switches are
    not specified in the examples below.

Run only the tests from the sale module:

.. code-block:: console

    $ odoo-bin --test-enable --test-tags sale

Run the tests from the sale module but not the ones tagged as slow:

.. code-block:: console

    $ odoo-bin --test-enable --test-tags 'sale,-slow'

Run only the tests from stock or tagged as slow:

.. code-block:: console

    $ odoo-bin --test-enable --test-tags '-standard, slow, stock'

.. note:: ``-standard`` is implicit (not required), and present for clarity

Testing JS code
===============

Qunit test suite
----------------

Odoo Web includes means to unit-test both the core code of
Odoo Web and your own javascript modules. On the javascript side,
unit-testing is based on QUnit_ with a number of helpers and
extensions for better integration with Odoo.

To see what the runner looks like, find (or start) an Odoo server
with the web client enabled, and navigate to ``/web/tests``
This will show the runner selector, which lists all modules with javascript
unit tests, and allows starting any of them (or all javascript tests in all
modules at once).

.. image:: ./images/runner.png
    :align: center

Clicking any runner button will launch the corresponding tests in the
bundled QUnit_ runner:

.. image:: ./images/tests.png
    :align: center

Writing a test case
-------------------

This section will be updated as soon as possible.

.. _qunit: http://qunitjs.com/


Integration Testing
===================

Testing Python code and JS code separately is very useful, but it does not prove
that the web client and the server work together.  In order to do that, we can
write another kind of test: tours.  A tour is a mini scenario of some interesting
business flow.  It explains a sequence of steps that should be followed.  The
test runner will then create a phantom_js browser, point it to the proper url
and simulate the click and inputs, according to the scenario.
