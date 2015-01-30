.. _reference/testing:

===============
Testing Modules
===============

Odoo provides support for testing modules using unittest2_.

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

.. autoclass:: openerp.tests.common.TransactionCase
    :members: browse_ref, ref

.. autoclass:: openerp.tests.common.SingleTransactionCase
    :members: browse_ref, ref

By default, tests are run once right after the corresponding module has been
installed. Test cases can also be configured to run after all modules have
been installed, and not run right after the module installation:

.. autofunction:: openerp.tests.common.at_install

.. autofunction:: openerp.tests.common.post_install

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

Running tests
-------------

Tests are automatically run when installing or updating modules if
:option:`--test-enable <odoo.py --test-enable>` was enabled when starting the
Odoo server.

As of Odoo 8, running tests outside of the install/update cycle is not
supported.

.. _unittest2: http://pypi.python.org/pypi/unittest2
.. _unittest documentation: https://docs.python.org/2/library/unittest.html
