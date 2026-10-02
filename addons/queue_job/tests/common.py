# Copyright 2019 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import doctest
import logging
import sys
import typing
from contextlib import contextmanager
from itertools import groupby
from operator import attrgetter
from unittest import TestCase, mock

from odoo.addons.queue_job.delay import Graph

# pylint: disable=odoo-addons-relative-import
from odoo.addons.queue_job.job import Job


@contextmanager
def trap_jobs():
    """Context Manager used to test enqueuing of jobs

    Trapping jobs allows to split the tests in:

    * the part that delays the job with the expected arguments in one test
    * the execution of the job itself in a second test

    When the jobs are trapped, they are not executed at all, however, we
    can verify they have been enqueued with the correct arguments and
    properties.

    Then in a second test, we can call the job method directly with the
    arguments to test.

    The context manager yields a instance of ``JobsTrap``, which provides
    utilities and assert methods.

    Example of method to test::

        def button_that_uses_delayable_chain(self):
            delayables = chain(
                self.delayable(
                    channel="root.test",
                    description="Test",
                    eta=15,
                    identity_key=identity_exact,
                    max_retries=1,
                    priority=15,
                ).testing_method(1, foo=2),
                self.delayable().testing_method('x', foo='y'),
                self.delayable().no_description(),
            )
            delayables.delay()

    Example of usage in a test::

        with trap_jobs() as trap:
            self.env['test.queue.job'].button_that_uses_delayable_chain()

            trap.assert_jobs_count(3)
            trap.assert_jobs_count(
                2, only=self.env['test.queue.job'].testing_method

            )
            trap.assert_jobs_count(
                1, only=self.env['test.queue.job'].no_description
            )

            trap.assert_enqueued_job(
                self.env['test.queue.job'].testing_method,
                args=(1,),
                kwargs={"foo": 2},
                properties=dict(
                    channel="root.test",
                    description="Test",
                    eta=15,
                    identity_key=identity_exact,
                    max_retries=1,
                    priority=15,
                )
            )
            trap.assert_enqueued_job(
                self.env['test.queue.job'].testing_method,
                args=("x",),
                kwargs={"foo": "y"},
            )
            trap.assert_enqueued_job(
                self.env['test.queue.job'].no_description,
            )

            # optionally, you can perform the jobs synchronously (without going
            # to the database)
            jobs_tester.perform_enqueued_jobs()
    """
    with mock.patch(
        "odoo.addons.queue_job.delay.Job",
        name="Job Class",
        auto_spec=True,
        unsafe=True,
    ) as job_cls_mock:
        with JobsTrap(job_cls_mock) as trap:
            yield trap


class JobCall(typing.NamedTuple):
    method: typing.Callable
    args: tuple
    kwargs: dict
    properties: dict

    def __eq__(self, other):
        if not isinstance(other, JobCall):
            return NotImplemented
        return (
            self.method.__self__ == other.method.__self__
            and self.method.__func__ == other.method.__func__
            and self.args == other.args
            and self.kwargs == other.kwargs
            and self.properties == other.properties
        )


class JobsTrap:
    """Used by ``trap_jobs()``, provide assert methods on the trapped jobs

    Look the documentation of ``trap_jobs()`` for a usage example.

    The ``store`` method of the Job instances is mocked so they are never
    saved in database.

    Helpers for tests:

    * ``jobs_count``
    * ``assert_jobs_count``
    * ``assert_enqueued_job``
    * ``perform_enqueued_jobs``

    You can also access the list of calls that were made to enqueue the jobs in
    the ``calls`` attribute, and the generated jobs in the ``enqueued_jobs``.
    """

    def __init__(self, job_mock):
        self.job_mock = job_mock
        self.job_mock.side_effect = self._add_job
        # 1 call == 1 job, they share the same position in the lists
        self.calls = []
        self.enqueued_jobs = []
        self._store_patchers = []
        self._test_case = TestCase()

    def jobs_count(self, only=None):
        """Return the count of enqueued jobs

        ``only`` is an option method on which the count is filtered
        """
        if only:
            return len(self._filtered_enqueued_jobs(only))
        return len(self.enqueued_jobs)

    def assert_jobs_count(self, expected, only=None):
        """Raise an assertion error if the count of enqueued jobs does not match

        ``only`` is an option method on which the count is filtered
        """
        self._test_case.assertEqual(self.jobs_count(only=only), expected)

    def assert_enqueued_job(self, method, args=None, kwargs=None, properties=None):
        """Raise an assertion error if the expected method has not been enqueued

        * ``method`` is the method (as method object) delayed as job
        * ``args`` is a tuple of arguments passed to the job method
        * ``kwargs`` is a dict of keyword arguments passed to the job method
        * ``properties`` is a dict of job properties (priority, eta, ...)

        The args and the kwargs *must* be match exactly what has been enqueued
        in the job method. The properties are optional: if the job has been
        enqueued with a custom description but the assert method is not called
        with ``description`` in the properties, it still matches the call.
        However, if a ``description`` is passed in the assert's properties, it
        must match.
        """
        if properties is None:
            properties = {}
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        expected_call = JobCall(
            method=method,
            args=args,
            kwargs=kwargs,
            properties=properties,
        )
        actual_calls = []
        for call in self.calls:
            checked_properties = {
                key: value
                for key, value in call.properties.items()
                if key in properties
            }
            # build copy of calls with only the properties that we want to
            # check
            actual_calls.append(
                JobCall(
                    method=call.method,
                    args=call.args,
                    kwargs=call.kwargs,
                    properties=checked_properties,
                )
            )

        if expected_call not in actual_calls:
            raise AssertionError(
                "Job %s was not enqueued.\n"
                "Actual enqueued jobs:\n%s"
                % (
                    self._format_job_call(expected_call),
                    "\n".join(
                        " * %s" % (self._format_job_call(call),)
                        for call in actual_calls
                    ),
                )
            )

    def perform_enqueued_jobs(self):
        """Perform the enqueued jobs synchronously"""

        def by_graph(job):
            return job.graph_uuid or ""

        sorted_jobs = sorted(self.enqueued_jobs, key=by_graph)
        self.enqueued_jobs = []
        for graph_uuid, jobs in groupby(sorted_jobs, key=by_graph):
            if graph_uuid:
                self._perform_graph_jobs(jobs)
            else:
                self._perform_single_jobs(jobs)

    def _perform_single_jobs(self, jobs):
        # we probably don't want to replicate a perfect order here, but at
        # least respect the priority
        for job in sorted(jobs, key=attrgetter("priority")):
            job.perform()

    def _perform_graph_jobs(self, jobs):
        graph = Graph()
        for job in jobs:
            graph.add_vertex(job)
            for parent in job.depends_on:
                graph.add_edge(parent, job)

        for job in graph.topological_sort():
            job.perform()

    def _add_job(self, *args, **kwargs):
        job = Job(*args, **kwargs)
        if not job.identity_key or all(
            j.identity_key != job.identity_key for j in self.enqueued_jobs
        ):
            self.enqueued_jobs.append(job)

            patcher = mock.patch.object(job, "store")
            self._store_patchers.append(patcher)
            patcher.start()

        job_args = kwargs.pop("args", None) or ()
        job_kwargs = kwargs.pop("kwargs", None) or {}
        self.calls.append(
            JobCall(
                method=args[0],
                args=job_args,
                kwargs=job_kwargs,
                properties=kwargs,
            )
        )
        return job

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for patcher in self._store_patchers:
            patcher.stop()

    def _filtered_enqueued_jobs(self, job_method):
        enqueued_jobs = [
            job
            for job in self.enqueued_jobs
            if job.func.__self__ == job_method.__self__
            and job.func.__func__ == job_method.__func__
        ]
        return enqueued_jobs

    def _format_job_call(self, call):
        method_all_args = []
        if call.args:
            method_all_args.append(", ".join("%s" % (arg,) for arg in call.args))
        if call.kwargs:
            method_all_args.append(
                ", ".join("%s=%s" % (key, value) for key, value in call.kwargs.items())
            )
        return "<%s>.%s(%s) with properties (%s)" % (
            call.method.__self__,
            call.method.__name__,
            ", ".join(method_all_args),
            ", ".join("%s=%s" % (key, value) for key, value in call.properties.items()),
        )

    def __repr__(self):
        return repr(self.calls)


class JobCounter:
    def __init__(self, env):
        super().__init__()
        self.env = env
        self.existing = self.search_all()

    def count_all(self):
        return len(self.search_all())

    def count_created(self):
        return len(self.search_created())

    def count_existing(self):
        return len(self.existing)

    def search_created(self):
        return self.search_all() - self.existing

    def search_all(self):
        return self.env["queue.job"].search([])


class JobMixin:
    def job_counter(self):
        return JobCounter(self.env)

    def perform_jobs(self, jobs):
        for job in jobs.search_created():
            Job.load(self.env, job.uuid).perform()

    @contextmanager
    def trap_jobs(self):
        with trap_jobs() as trap:
            yield trap


@contextmanager
def mock_with_delay():
    """Context Manager mocking ``with_delay()``

    DEPRECATED: use ``trap_jobs()'``.

    Mocking this method means we can decorrelate the tests in:

    * the part that delay the job with the expected arguments
    * the execution of the job itself

    The first kind of test does not need to actually create the jobs in the
    database, as we can inspect how the Mocks were called.

    The second kind of test calls directly the method decorated by ``@job``
    with the arguments that we want to test.

    The context manager returns 2 mocks:
    * the first allow to check that with_delay() was called and with which
      arguments
    * the second to check which job method was called and with which arguments.

    Example of test::

        def test_export(self):
            with mock_with_delay() as (delayable_cls, delayable):
                # inside this method, there is a call
                # partner.with_delay(priority=15).export_record('test')
                self.record.run_export()

                # check 'with_delay()' part:
                self.assertEqual(delayable_cls.call_count, 1)
                # arguments passed in 'with_delay()'
                delay_args, delay_kwargs = delayable_cls.call_args
                self.assertEqual(
                    delay_args, (self.env['res.partner'],)
                )
                self.assertDictEqual(delay_kwargs, {priority: 15})

                # check what's passed to the job method 'export_record'
                self.assertEqual(delayable.export_record.call_count, 1)
                delay_args, delay_kwargs = delayable.export_record.call_args
                self.assertEqual(delay_args, ('test',))
                self.assertDictEqual(delay_kwargs, {})

    An example of the first kind of test:
    https://github.com/camptocamp/connector-jira/blob/0ca4261b3920d5e8c2ae4bb0fc352ea3f6e9d2cd/connector_jira/tests/test_batch_timestamp_import.py#L43-L76  # noqa
    And the second kind:
    https://github.com/camptocamp/connector-jira/blob/0ca4261b3920d5e8c2ae4bb0fc352ea3f6e9d2cd/connector_jira/tests/test_import_task.py#L34-L46  # noqa

    """
    with mock.patch(
        "odoo.addons.queue_job.models.base.DelayableRecordset",
        name="DelayableRecordset",
        spec=True,
    ) as delayable_cls:
        # prepare the mocks
        delayable = mock.MagicMock(name="DelayableBinding")
        delayable_cls.return_value = delayable
        yield delayable_cls, delayable


class OdooDocTestCase(doctest.DocTestCase):
    """
    We need a custom DocTestCase class in order to:
    - define test_tags to run as part of standard tests
    - output a more meaningful test name than default "DocTestCase.runTest"
    """

    def __init__(
        self, doctest, optionflags=0, setUp=None, tearDown=None, checker=None, seq=0
    ):
        super().__init__(
            doctest._dt_test,
            optionflags=optionflags,
            setUp=setUp,
            tearDown=tearDown,
            checker=checker,
        )
        self.test_sequence = seq

    def setUp(self):
        """Log an extra statement which test is started."""
        super(OdooDocTestCase, self).setUp()
        logging.getLogger(__name__).info("Running tests for %s", self._dt_test.name)


def load_doctests(module):
    """
    Generates a tests loading method for the doctests of the given module
    https://docs.python.org/3/library/unittest.html#load-tests-protocol
    """

    def load_tests(loader, tests, ignore):
        """
        Apply the 'test_tags' attribute to each DocTestCase found by the DocTestSuite.
        Also extend the DocTestCase class trivially to fit the class teardown
        that Odoo backported for its own test classes from Python 3.8.
        """
        if sys.version_info < (3, 8):
            doctest.DocTestCase.doClassCleanups = lambda: None
            doctest.DocTestCase.tearDown_exceptions = []

        for idx, test in enumerate(doctest.DocTestSuite(module)):
            odoo_test = OdooDocTestCase(test, seq=idx)
            odoo_test.test_tags = {"standard", "at_install", "queue_job", "doctest"}
            tests.addTest(odoo_test)

        return tests

    return load_tests
