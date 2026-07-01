# Copyright (c) 2015-2016 ACSONE SA/NV (<http://acsone.eu>)
# Copyright 2013-2016 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import logging
import random
import time
import traceback
from io import StringIO

from psycopg2 import OperationalError, errorcodes
from werkzeug.exceptions import BadRequest, Forbidden

from odoo import SUPERUSER_ID, _, api, http, registry, tools
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY

from ..delay import chain, group
from ..exception import FailedJobError, NothingToDoJob, RetryableJobError
from ..job import ENQUEUED, Job

_logger = logging.getLogger(__name__)

PG_RETRY = 5  # seconds

DEPENDS_MAX_TRIES_ON_CONCURRENCY_FAILURE = 5


class RunJobController(http.Controller):
    def _try_perform_job(self, env, job):
        """Try to perform the job."""
        job.set_started()
        job.store()
        env.cr.commit()
        _logger.debug("%s started", job)

        job.perform()
        # Triggers any stored computed fields before calling 'set_done'
        # so that will be part of the 'exec_time'
        env.flush_all()
        job.set_done()
        job.store()
        env.flush_all()
        env.cr.commit()
        _logger.debug("%s done", job)

    def _enqueue_dependent_jobs(self, env, job):
        tries = 0
        while True:
            try:
                job.enqueue_waiting()
            except OperationalError as err:
                # Automatically retry the typical transaction serialization
                # errors
                if err.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise
                if tries >= DEPENDS_MAX_TRIES_ON_CONCURRENCY_FAILURE:
                    _logger.info(
                        "%s, maximum number of tries reached to update dependencies",
                        errorcodes.lookup(err.pgcode),
                    )
                    raise
                wait_time = random.uniform(0.0, 2**tries)
                tries += 1
                _logger.info(
                    "%s, retry %d/%d in %.04f sec...",
                    errorcodes.lookup(err.pgcode),
                    tries,
                    DEPENDS_MAX_TRIES_ON_CONCURRENCY_FAILURE,
                    wait_time,
                )
                time.sleep(wait_time)
            else:
                break

    @http.route("/queue_job/runjob", type="http", auth="none", save_session=False)
    def runjob(self, db, job_uuid, **kw):
        http.request.session.db = db
        env = http.request.env(user=SUPERUSER_ID)

        def retry_postpone(job, message, seconds=None):
            job.env.clear()
            with registry(job.env.cr.dbname).cursor() as new_cr:
                job.env = api.Environment(new_cr, SUPERUSER_ID, {})
                job.postpone(result=message, seconds=seconds)
                job.set_pending(reset_retry=False)
                job.store()

        # ensure the job to run is in the correct state and lock the record
        env.cr.execute(
            "SELECT state FROM queue_job WHERE uuid=%s AND state=%s FOR UPDATE",
            (job_uuid, ENQUEUED),
        )
        if not env.cr.fetchone():
            _logger.warning(
                "was requested to run job %s, but it does not exist, "
                "or is not in state %s",
                job_uuid,
                ENQUEUED,
            )
            return ""

        job = Job.load(env, job_uuid)
        assert job and job.state == ENQUEUED

        try:
            try:
                self._try_perform_job(env, job)
            except OperationalError as err:
                # Automatically retry the typical transaction serialization
                # errors
                if err.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise

                _logger.debug("%s OperationalError, postponed", job)
                raise RetryableJobError(
                    tools.ustr(err.pgerror, errors="replace"), seconds=PG_RETRY
                ) from err

        except NothingToDoJob as err:
            if str(err):
                msg = str(err)
            else:
                msg = _("Job interrupted and set to Done: nothing to do.")
            job.set_done(msg)
            job.store()
            env.cr.commit()

        except RetryableJobError as err:
            # delay the job later, requeue
            retry_postpone(job, str(err), seconds=err.seconds)
            _logger.debug("%s postponed", job)
            # Do not trigger the error up because we don't want an exception
            # traceback in the logs we should have the traceback when all
            # retries are exhausted
            env.cr.rollback()
            return ""

        except (FailedJobError, Exception) as orig_exception:
            buff = StringIO()
            traceback.print_exc(file=buff)
            traceback_txt = buff.getvalue()
            _logger.error(traceback_txt)
            job.env.clear()
            with registry(job.env.cr.dbname).cursor() as new_cr:
                job.env = job.env(cr=new_cr)
                vals = self._get_failure_values(job, traceback_txt, orig_exception)
                job.set_failed(**vals)
                job.store()
                buff.close()
            raise

        _logger.debug("%s enqueue depends started", job)
        self._enqueue_dependent_jobs(env, job)
        _logger.debug("%s enqueue depends done", job)

        return ""

    def _get_failure_values(self, job, traceback_txt, orig_exception):
        """Collect relevant data from exception."""
        exception_name = orig_exception.__class__.__name__
        if hasattr(orig_exception, "__module__"):
            exception_name = orig_exception.__module__ + "." + exception_name
        exc_message = getattr(orig_exception, "name", str(orig_exception))
        return {
            "exc_info": traceback_txt,
            "exc_name": exception_name,
            "exc_message": exc_message,
        }

    # flake8: noqa: C901
    @http.route("/queue_job/create_test_job", type="http", auth="user")
    def create_test_job(
        self,
        priority=None,
        max_retries=None,
        channel=None,
        description="Test job",
        size=1,
        failure_rate=0,
    ):
        """Create test jobs

        Examples of urls:

        * http://127.0.0.1:8069/queue_job/create_test_job: single job
        * http://127.0.0.1:8069/queue_job/create_test_job?size=10: a graph of 10 jobs
        * http://127.0.0.1:8069/queue_job/create_test_job?size=10&failure_rate=0.5:
          a graph of 10 jobs, half will fail

        """
        if not http.request.env.user.has_group("base.group_erp_manager"):
            raise Forbidden(_("Access Denied"))

        if failure_rate is not None:
            try:
                failure_rate = float(failure_rate)
            except (ValueError, TypeError):
                failure_rate = 0

        if not (0 <= failure_rate <= 1):
            raise BadRequest("failure_rate must be between 0 and 1")

        if size is not None:
            try:
                size = int(size)
            except (ValueError, TypeError):
                size = 1

        if priority is not None:
            try:
                priority = int(priority)
            except ValueError:
                priority = None

        if max_retries is not None:
            try:
                max_retries = int(max_retries)
            except ValueError:
                max_retries = None

        if size == 1:
            return self._create_single_test_job(
                priority=priority,
                max_retries=max_retries,
                channel=channel,
                description=description,
                failure_rate=failure_rate,
            )

        if size > 1:
            return self._create_graph_test_jobs(
                size,
                priority=priority,
                max_retries=max_retries,
                channel=channel,
                description=description,
                failure_rate=failure_rate,
            )
        return ""

    def _create_single_test_job(
        self,
        priority=None,
        max_retries=None,
        channel=None,
        description="Test job",
        size=1,
        failure_rate=0,
    ):
        delayed = (
            http.request.env["queue.job"]
            .with_delay(
                priority=priority,
                max_retries=max_retries,
                channel=channel,
                description=description,
            )
            ._test_job(failure_rate=failure_rate)
        )
        return "job uuid: %s" % (delayed.db_record().uuid,)

    TEST_GRAPH_MAX_PER_GROUP = 5

    def _create_graph_test_jobs(
        self,
        size,
        priority=None,
        max_retries=None,
        channel=None,
        description="Test job",
        failure_rate=0,
    ):
        model = http.request.env["queue.job"]
        current_count = 0

        possible_grouping_methods = (chain, group)

        tails = []  # we can connect new graph chains/groups to tails
        root_delayable = None
        while current_count < size:
            jobs_count = min(
                size - current_count, random.randint(1, self.TEST_GRAPH_MAX_PER_GROUP)
            )

            jobs = []
            for __ in range(jobs_count):
                current_count += 1
                jobs.append(
                    model.delayable(
                        priority=priority,
                        max_retries=max_retries,
                        channel=channel,
                        description="%s #%d" % (description, current_count),
                    )._test_job(failure_rate=failure_rate)
                )

            grouping = random.choice(possible_grouping_methods)
            delayable = grouping(*jobs)
            if not root_delayable:
                root_delayable = delayable
            else:
                tail_delayable = random.choice(tails)
                tail_delayable.on_done(delayable)
            tails.append(delayable)

        root_delayable.delay()

        return "graph uuid: %s" % (
            list(root_delayable._head())[0]._generated_job.graph_uuid,
        )
