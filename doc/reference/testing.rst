:banner: banners/testing_modules.jpg

.. _reference/testing:


===============
Testing Modules
===============

Odoo provides support for testing modules using pytest_.

To write tests, simply define a ``tests`` sub-package in your module. It
*must* have an empty ``__init__.py`` and will contain your test modules. The
test modules should be named :samp:`test_{modname}.py`

.. code-block:: text

    your_module
    |-- ...
    `-- tests
        |-- __init__.py
        |-- test_bar.py
        `-- test_foo.py

.. versionchanged:: 9.0

    previously, only test modules imported from ``tests/__init__.py`` would be
    run. Starting in 9.0, all test modules are matched and run automatically.

    To skip or disable tests, they must be explicitly marked using
    :ref:`unittest.skip <unittest-skipping>` or
    `pytest.mark.skipif <http://pytest.org/latest/skipping.html>`_.

The test runner will run both `unittest-style <unittest>`_ class-based tests
and `pytest-style <pytest-cases>`_ function-based tests, matching tests based
on `pytest's standard discovery conventions
<http://pytest.org/latest/goodpractises.html#test-discovery>`_

.. note:: the test runner will also run yaml and XML test files specified via
          the ``tests`` key of a :ref:`module's manifest
          <reference/module/manifest>`.

Unittest-style cases
====================

For integration with the Odoo system, Odoo provides two utility subclasses of
:class:`python:unittest.TestCase` managing transaction state and providing
access to an Odoo :class:`~openerp.api.Environment`:

.. autoclass:: openerp.tests.common.TransactionCase

.. autoclass:: openerp.tests.common.SingleTransactionCase

The most common situation is to use
:class:`~openerp.tests.common.TransactionCase` and test a property of a model
in each method::

    class TestModelA(common.TransactionCase):
        def test_some_action(self):
            record = self.env['model.a'].create({'field': 'value'})
            record.some_action()
            self.assertEqual(
                record.field,
                expected_field_value)

        # other tests...

Pytest-style cases
==================

Pytest-style cases are just test functions whose names match the `discovery
conventions <http://pytest.org/latest/goodpractises.html#test-discovery>`_.
Rather than use special ``assert*`` methods, they just use the standard
``assert`` statement::

    def test_action():
        assert 1 + 1 == 2
    # other tests

Integration with the Odoo system is provided via a `pytest fixture
<http://pytest.org/latest/fixture.html>`_ ``env``, which provides the same
service as :attr:`openerp.tests.common.TransactionCase.env`::

    def test_action(env):
        record = env['model.a'].create({'field': 'value'})
        record.some_action()
        assert record.field == expected_field_value

    # other tests

Test data and setup/teardown behaviour can be provided using `in-module
fixtures <http://pytest.org/latest/fixture.html#fixtures-as-function-arguments>`_::

    import pytest

    @pytest.fixture
    def records(env):
        ModelA = env['model.a']
        ModelA.create({'field': 'value'})
        ModelA.create({'field': 'value2'})

    def test_action(env, records):
        record = env['model.a'].search([('field', '=', 'value')])
        record.some_action()
        assert record.field == expected_field_value

    def test_action2(env, records):
        # gets a brand new version of records in a separate transaction
        record2 = env['model.a'].search([('field', '=', 'value2')])
        record2.some_action()
        assert record2.field == expected_field_value2

Pytest fixtures for Odoo
------------------------

.. automodule:: openerp.tests.fixtures
    :members:
    :member-order: bysource

Cross-style utilities
=====================

By default, Python tests are run once at the end of the corresponding module's
installation. Test cases can also be configured to run after all modules have
been installed, and not run during the module's installation, by *marking*
them with the following decorators:

.. function:: pytest.mark.at_install(flag)

    * if the flag is ``True``, will schedule the test to run during the
      module's installation
    * if the flag is ``False``, will skip the test during the module's
      installation

.. function:: pytest.mark.post_install(flag)

    * if the flag is ``True``, will schedule the test to run after all modules
      have been installed
    * if the flag is ``False``, will skip the test after all modules have been
      installed

* By default, tests are run ``at_install`` and not run ``post_install``
  (they're implicitly decorated with ``at_install(True)`` and
  ``post_install(False)``
* Using unittest-style cases, it is possible to decorate both class and test
  method. A test class's decoration will apply to all of its test methods,
  a test method's decoration will override the classe's.

Running tests
=============

* tests can be run using the :ref:`odoo.py test <reference/cmdline/testing>`
  command, providing addons or directories whose tests should be run (and
  which should be installed if necessary)
* tests can also be run while installing or updating modules if
  :option:`--test-enable <odoo.py --test-enable>` is set when starting the
  Odoo server.

.. _pytest: http://pytest.org
.. _pytest-cases: http://pytest.org/latest/getting-started.html
.. _unittest: https://docs.python.org/2/library/unittest.html
