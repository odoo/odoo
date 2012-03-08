.. _test-framework:

Test framework
==============

In addition to the YAML-based tests, OpenERP uses the unittest2_ testing
framework to test both the core ``openerp`` package and its addons. For the
core and each addons, tests are divided between three (overlapping) sets:

1. A test suite that comprises all the tests that can be run right after the
   addons is installed (or, for the core, right after a database is created).
   That suite is called ``fast_suite`` and must contain only tests that can be run
   frequently. Actually most of the tests should be considered fast enough to be
   included in that ``fast_suite`` list and only tests that take a long time to run
   (e.g. more than a minute) should not be listed. Those long tests should come up
   pretty rarely.

2. A test suite called ``checks`` provides sanity checks. These tests are
   invariants that must be full-filled at any time. They are expected to always
   pass: obviously they must pass right after the module is installed (i.e. just
   like the ``fast_suite`` tests), but they must also pass after any other module is
   installed, after a migration, or even after the database was put in production
   for a few months.

3. The third suite is made of all the tests: those provided by the two above
   suites, but also tests that are not explicitely listed in ``fast_suite`` or
   ``checks``. They are not explicitely listed anywhere and are discovered
   automatically.

As the sanity checks provide stronger guarantees about the code and database
structure, new tests must be added to the ``checks`` suite whenever it is
possible. Said with other words: one should try to avoid writing tests that
assume a freshly installed/unaltered module or database.

It is possible to have tests that are not listed in ``fast_suite`` or
``checks``.  This is useful if a test takes a lot of time. By default, when
using the testing infrastructure, tests should run fast enough so that people
can use them frequently. One can also use that possiblity for tests that
require some complex setup before they can be successfuly run.

As a rule of thumb when writing a new test, try to add it to the ``checks``
suite. If it really needs that the module it belongs to is freshly installed,
add it to ``fast_suite``. Finally, if it can not be run in an acceptable time
frame, don't add it to any explicit list.

Writing tests
-------------

The tests must be developed under ``<addons-name>.tests`` (or ``openerp.tests``
for the core).  For instance, with respect to the tests, a module ``foo``
should be organized as follow::

  foo/
    __init__.py # does not import .tests
    tests/
      __init__.py # import some of the tests sub-modules, and
                  # list them in fast_suite or checks
      test_bar.py # contains unittest2 classes
      test_baz.py # idem
      ... and so on ...

The two explicit lists of tests are thus the variables ``foo.tests.fast_suite``
and ``foo.tests.checks``. As an example, you can take a look at the
``openerp.tests`` module (which follows exactly the same conventions even if it
is not an addons).

Note that the ``fast_suite`` and ``checks`` variables are really lists of
module objects. They could be directly unittest2 suite objects if necessary in
the future.

Running the tests
-----------------

To run the tests (see :ref:`above <test-framework>` to learn how tests are
organized), the simplest way is to use the ``oe`` command (provided by the
``openerp-command`` project).

::

  > oe run-tests # will run all the fast_suite tests
  > oe run-tests -m openerp # will run all the fast_suite tests defined in `openerp.tests`
  > oe run-tests -m sale # will run all the fast_suite tests defined in `openerp.addons.sale.tests`
  > oe run-tests -m foo.test_bar # will run the tests defined in `openerp.addons.foo.tests.test_bar`

In addition to the above possibilities, when invoked with a non-existing module
(or module.sub-module) name, oe will reply with a list of available test
sub-modules.

Depending on the unittest2_ class that is used to write the tests (see
``openerp.tests.common`` for some helper classes that you can re-use), a database
may be created before the test is run, and the module providing the test will
be installed on that database.

Because creating a database, installing modules, and then dropping it is
expensive, it is possible to interleave the run of the ``fast_suite`` tests
with the initialization of a new database: the dabase is created, and after
each requested module is installed, its fast_suite tests are run. The database
is thus created and dropped (and the modules installed) only once.

.. _unittest2: http://pypi.python.org/pypi/unittest2
