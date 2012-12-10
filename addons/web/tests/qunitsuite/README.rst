QUnitSuite is a ``unittest.TestSuite`` able to run QUnit_ test suites
within the normal unittest process, through PhantomJS_.

QUnitSuite is built upon `Ben Alman`_'s work of for the interfacing
between PhantomJS_ and the host/reporting code: the shims and the
PhantomJS_ configuration files are those of grunt_'s ``qunit`` task.

Why
---

You're a Python shop or developer, you have tools and tests built
around unittest (or compatible with unittests) and your testing
pipeline is predicated upon that, you're doing web development of some
sort these days (as so many are) and you'd like to do some testing of
your web stuff.

But you don't really want to redo your whole testing stack just for
that.

QUnitSuite simply grafts QUnit_-based tests, run in PhantomJS_, in
your existing ``unittest``-based architecture.

What
----

QUnitSuite currently provides a single object as part of its API:
``qunitsuite.QUnitSuite(testfile[, timeout])``.

This produces a ``unittest.TestSuite`` suitable for all the usual
stuff (running it, and giving it to an other test suite which will run
it, that is).

``testfile`` is the HTML file bootstrapping your qunit tests, as would
usually be accessed via a browser. It can be either a local
(``file:``) url, or an HTTP one. As long as a regular browser can open
and execute it, PhantomJS_ will manage.

``timeout`` is a check passed to the PhantomJS_ runner: if the runner
produces no information for longer than ``timeout`` milliseconds, the
run will be cancelled and a test error will be generated. This
situation usually means either your ``testfile`` is not a qunit test
file, qunit is not running or qunit's runner was stopped (for an async
test) and never restarted.

The default value is very conservative, most tests should run
correctly with lower timeouts (especially if all tests are
synchronous).

How
---

``unittest``'s autodiscovery protocol does not directly work with test
suites (it looks for test cases). If you want autodiscovery to work
correctly, you will have to use the ``load_tests`` protocol::

    # in a testing module
    def load_tests(loader, tests, pattern):
        tests.addTest(QUnitSuite(qunit_test_path.html))
        return tests

outside of that specific case, you can use a ``QUnitSuite`` as a
standard ``TestSuite`` instance, running it, adding it to an other
suite or passing it to a ``TestRunner``

Complaints and Grievances
-------------------------

Speed
~~~~~

Starting up a phantomjs instance and running a suite turns out to have
a rather high overhead, on the order of a second on this machine
(2.4GHz, 8GB RAM and an SSD).

As each ``QUnitSuite`` currently creates its own phantomjs instance,
it's probably a good idea to create bigger suites (put many modules &
tests in the same QUnit html file, which doesn't preclude splitting
them across multiple js files).

Hacks
~~~~~

QUnitSuite contains a pretty big hack which may or may not cause
problem depending on your exact setup: in case of case failure or
error, ``unittest.TestResult`` formats the error traceback provided
alongside the test object. This goes through Python's
traceback-formatting code and there are no hooks there.

One could expect to use a custom ``TestResult``, but for test suites
the ``TestResult`` instance must be provided by the caller, so there
is no direct hook onto it.

This leaves three options:

* Create a custom ``TestResult`` class and require that it be the one
  provided to the test suite. This requires altered work flows,
  customization of the test runner and (as far as I know) isn't
  available through Python 2.7's autodiscovery. It's the cleanest
  option but completely fails on practicality.

* Create a custom ``TestResult`` which directly alters the original
  result's ``errors`` and ``failures`` attributes as they're part of
  the testrunner API. This would work but may put custom results in a
  strange state and break e.g. unittest2's ``@failfast``.

* Lastly, monkeypatch the undocumented and implementation detail
  ``_exc_info_to_string`` on the provided ``result``. This is the
  route taken, at least for now.

.. _QUnit: http://qunitjs.com/

.. _PhantomJS: http://phantomjs.org/

.. _Ben Alman: http://benalman.com/

.. _grunt: http://gruntjs.com/
