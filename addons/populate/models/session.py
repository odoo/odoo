from __future__ import annotations

import importlib
import json
import logging
import math
import multiprocessing as mp
import os
import secrets
import sys
import time
from abc import ABC, abstractmethod
from ast import literal_eval
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Self

import psycopg2
from psycopg2.errors import (
    CheckViolation,
    ExclusionViolation,
    NotNullViolation,
    UniqueViolation,
)

from odoo import SUPERUSER_ID, api, fields, models, modules
from odoo.exceptions import ConcurrencyError, LockError, UserError, ValidationError
from odoo.fields import Domain
from odoo.http.retrying import retrying
from odoo.modules.registry import Registry
from odoo.tools import SQL, config, profiler, str2bool

from ..utils.profiling import POPULATE_PROFILE_SESSION_KEY, get_profile_session_name
from ..utils.seed import derive_seed_from
from .job import get_execution_scope

if TYPE_CHECKING:
    from collections.abc import Callable

    from .job import Job

PG_EXCEPTIONS_TO_RETRY = (
    CheckViolation,
    ExclusionViolation,
    NotNullViolation,
    UniqueViolation,
)
POPULATE_SESSION_LOCK_NAMESPACE = 'odoo.populate.session.running'

_worker_logger = logging.getLogger('odoo.addons.populate.worker')


def has_platform_enabled_multiprocessing() -> bool:
    """Checks if the platform has allowed multiprocessing for the `populate` feature."""
    # opt-in by default, easier user onboarding.
    return str2bool(os.getenv('ODOO_POPULATE_MULTIPROCESS_ENABLE', 'True'))


class Session(models.Model):
    """
    Single execution run of a blueprint.

    A session owns the full set of ``populate.job`` records produced
    from its blueprint and tracks their completion state.
    Interrupted sessions can be resumed — only pending jobs are re-executed.
    """
    _name = 'populate.session'
    _description = 'Data Population Session'

    seed = fields.Integer("Seed", default=lambda _: max(secrets.randbits(31) - 1, 0))
    scaling_factor = fields.Float("Scaling Factor")
    worker_count = fields.Integer("Number of parallel workers that will run jobs at the same time", default=1)
    blueprint_id = fields.Many2one('populate.blueprint', required=True, ondelete='cascade')
    job_ids = fields.One2many('populate.job', inverse_name='session_id', domain=[('parent_id', '=', False)])

    @api.constrains('job_ids')
    def _check_has_jobs(self):
        for session in self:
            if not session.job_ids:
                raise ValidationError(self.env._("A created session should have jobs associated from a blueprint."))

    @property
    def is_done(self) -> bool:
        return self.job_ids and all(self.job_ids.mapped('is_done'))

    @property
    def is_parallel(self) -> bool:
        return self.worker_count > 1

    @property
    def is_profiling(self) -> bool:
        return POPULATE_PROFILE_SESSION_KEY in self.env.context

    @property
    def profile_session_name(self) -> str | None:
        return self.env.context.get(POPULATE_PROFILE_SESSION_KEY)

    @property
    def pending_jobs(self):
        return self.job_ids.filtered(lambda job: not job.is_done)

    @property
    def progress(self) -> float:
        """Get the progress of the session as value between [0, 1]"""
        return sum(job.progress for job in self.job_ids) / (len(self.job_ids) or 1)

    @property
    def is_running(self) -> bool:
        """The session is running if its advisory lock is currently held."""
        self.ensure_one()

        lock_namespace, session_id = self._running_lock_key()
        return self.env.execute_query(SQL("""
            SELECT EXISTS (
                SELECT 1
                  FROM pg_locks
                 WHERE locktype = 'advisory'
                   -- For pg_advisory_lock(int, int), PostgreSQL stores the first key
                   -- in classid, the second key in objid, and marks objsubid as 2.
                   AND database = (
                        SELECT oid
                          FROM pg_database
                         WHERE datname = current_database()
                   )
                   AND classid::int = hashtext(%s)
                   AND objid::int = %s
                   AND objsubid = 2
                   -- Ignore processes waiting for the lock; only the holder means "running".
                   AND granted
            )
        """, lock_namespace, session_id))[0][0]

    def _running_lock_key(self):
        """Return the PostgreSQL advisory lock key used to guard this session.

        :return: Namespace and session id used as the two advisory lock parts.
        """
        return POPULATE_SESSION_LOCK_NAMESPACE, self.ensure_one().id

    @api.model_create_multi
    def create(self, vals_list):
        """Create sessions and instantiate their jobs from the selected blueprint.

        :param vals_list: Values for the new ``populate.session`` records.
        :return: Created session records.
        """
        sessions = super().create(vals_list)
        assert not sessions.job_ids

        for session in sessions:
            session._instantiate()

        return sessions

    def _instantiate(self):
        """Create new jobs to be run from the session's blueprint."""
        self.ensure_one()
        assert self.blueprint_id

        if self.job_ids:
            return  # Session already has jobs -> do nothing

        scaling_factor = self.scaling_factor or 1
        vals_list = []
        write_target_counts = defaultdict(lambda: defaultdict(int))  # {ref | None: {model_name: count}}
        for index, model in enumerate(self.blueprint_id.definition):
            model_name = model['name']
            ref, _, ref_relation = (part or None for part in model.get('ref', '').partition('.'))
            vals = {
                'model_name': model_name,
                'instructions': model['fields'],
                'session_id': self.id,
                'seed': derive_seed_from(self.seed, index),
            }
            if 'count' in model:
                factor = scaling_factor if model.get('scale', True) else 1
                vals['record_count'] = math.floor(model['count'] * factor)

            vals.update(**{k: v for k, v in model.items() if k in ('type', 'ref', 'parallel', 'context', 'domain')})

            defaults = self.env['populate.job'].default_get(['type', 'record_count'])
            is_create = vals.get('type', defaults['type']) == 'create'

            if is_create:
                write_target_counts[ref][model_name] += vals.get('record_count', defaults['record_count'])
            else:
                # Compute write job record_count:
                # - with 'ref': count from the matching 'create' job
                # - without 'ref': existing DB records + all preceding 'create' jobs for this model
                if ref:
                    assert ref in write_target_counts, f"Create 'refs' should be present before its' writes, missing: {ref}"
                    if ref_relation:
                        # The count of the corecords is unknown at creation time.
                        vals['record_count'] = None
                    else:
                        vals['record_count'] = write_target_counts[ref][model_name]
                else:
                    domain = Domain(literal_eval(vals['domain'])) if vals.get('domain') else Domain.TRUE
                    existing = self.env[model_name].with_context(active_test=False).search_count(domain)
                    from_creates = sum(
                        counts_by_model.get(model_name, 0)
                        for counts_by_model in write_target_counts.values()
                    )
                    total = existing + from_creates
                    if total > 0:
                        vals['record_count'] = total

            vals_list.append(vals)

        jobs = self.env['populate.job'].create(vals_list)
        jobs._create_subjobs()


class JobExecutor(ABC):
    """
    Abstract base class for job execution strategies.

    Selects the appropriate concrete executor based on the session configuration.
    Use as a context manager to get a ready-to-use executor::

        with JobExecutor.from_session(session) as executor:
            executor.execute(session.pending_jobs)
    """

    def __init__(self, session: Session) -> Self:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass

    @abstractmethod
    def execute(self, jobs: Job):
        """Execute a collection of jobs following the JobExecutor's strategy"""
        ...

    @staticmethod
    def _execute_with_retry(job: Job):
        """
        Execute a single job, with a retry mechanism on extended retrying conditions.

        For the SequentialExecutor, retrying is necessary for potential complex multi-field constraints
        that cannot be avoided with parameters in a blueprint.
        For the ParallelExecutor, retrying is a must for multi-worker serialization issues,
        in addition to the above-mentioned issues.

        :param job: Job or subjob to execute.
        """
        seed = job.seed
        retry_count = 0

        def execute_job():
            """
            Small wrapper to retry on additional database exceptions.

            Usually these exceptions are due to a user error,
            but in the context of populating data,
            they're due to randomness, so we want to retry on them
            instead of failing the populate session.
            """
            nonlocal seed, retry_count
            try:
                job._execute(seed=seed)
            except PG_EXCEPTIONS_TO_RETRY as exc:
                # Re-roll the seed in case of a violation
                # to avoid re-generating the same values,
                # leading to the same violation.
                seed = derive_seed_from(seed, retry_count)
                retry_count += 1

                error = psycopg2.errorcodes.lookup(exc.pgcode)

                msg = None
                if isinstance(exc, CheckViolation | ExclusionViolation):
                    msg = job.env._("Adapt the generator parameter to generate values within the constraint")
                if isinstance(exc, NotNullViolation):
                    msg = job.env._("The field is implicitly required, consider adding `null_ratio=0`")
                if isinstance(exc, UniqueViolation):
                    msg = job.env._("Consider using a generator (or combination of) that produces more varied values")

                raise ConcurrencyError(f"{error} ({msg})" if msg else error) from exc

        retrying(execute_job, job.env, close_on_commit=False)


class SequentialExecutor(JobExecutor):
    """
    Executes jobs one at a time in the current process.

    Jobs are run sequentially in the order they are provided.
    """

    def execute(self, jobs: Job):
        for job in jobs:
            self._execute_with_retry(job)


class ParallelExecutor(JobExecutor):
    """
    Executes jobs using a pool of worker sub-processes via ``ProcessPoolExecutor``.

    Parallel execution is only applied to jobs that have child subjobs *and* have
    ``parallel=True``; all other jobs fall back to in-process sequential execution.
    """

    def __init__(self, session: Session):
        super().__init__(session)
        self.dbname = session.env.cr.dbname
        assert session.worker_count > 1
        self.worker_count = session.worker_count
        self.pool: ProcessPoolExecutor | None = None
        self._options = dict(config.options)

    def __getstate__(self):
        payload = {
            'dbname': self.dbname,
            'worker_count': self.worker_count,
            # `ProcessPoolExecutor` cannot be pickled
            # due to an internal thread.lock.
            # A worker doesn't need the pool anyway.
            'pool': None,
            '_options': self._options,
        }
        json.dumps(payload)  # safety
        return payload

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.stop()

    @cached_property
    def _worker_init(self) -> Callable:
        """Load the worker initializer without importing through ``odoo.addons``.

        ``ProcessPoolExecutor`` with ``spawn`` imports the initializer before it
        runs it. Loading ``populate_worker`` as a top-level module avoids an
        early import of ``odoo.addons.populate``, which may only become
        available after the worker initializes Odoo's addons' path.
        """
        utils_path_str = str(Path(__file__).resolve().parents[1] / 'utils')
        if utils_path_str not in sys.path:
            # sys.path is inherited in the spawn
            sys.path.append(utils_path_str)
            importlib.invalidate_caches()

        # Import target: odoo/addons/populate/utils/populate_worker:initialize
        return importlib.import_module('populate_worker').initialize

    def _worker_execute(self, job_id: int, context: dict):
        """Execute a subjob inside a worker process with a fresh registry cursor.

        :param job_id: Database id of the subjob to execute.
        :param context: Serializable environment context copied from the parent process.
        """
        registry = Registry(self.dbname)
        with registry.cursor() as cr:
            uid = context['uid'] = SUPERUSER_ID
            env = api.Environment(cr, uid, context)
            job: Job = env['populate.job'].browse(job_id)

            assert job.exists()

            if job.context:
                job = job.with_context(**job.context)

            self._execute_with_retry(job)

    def start(self):
        """Start the process pool and eagerly initialize all workers."""
        _worker_logger.info(
            "Creating worker pool with %d processes for database '%s'",
            self.worker_count,
            self.dbname,
        )
        self.pool = ProcessPoolExecutor(
            max_workers=self.worker_count,
            initializer=self._worker_init,
            initargs=(self.dbname, self._options),
            mp_context=mp.get_context('spawn'),
        )
        # Eagerly spawn all workers at the beginning.
        # By default, they are lazily created only on the first jobs submitted.
        # There is no API exposed for this, so we submit dummy jobs.
        # A no-op task may finish before the executor has dispatched work to every worker;
        # sleeping briefly makes each dummy task last long enough for the pool to spawn.
        list(self.pool.map(time.sleep, [0.1] * self.worker_count))

    def stop(self):
        if self.pool:
            _worker_logger.info("Shutting down worker pool...")
            self.pool.shutdown(wait=True, cancel_futures=True)

    def execute(self, jobs: Job):
        """Execute pending jobs, dispatching eligible subjobs to worker processes.

        :param jobs: Top-level jobs to execute in blueprint order.
        """
        for job in jobs:
            if job.child_ids and job.parallel:
                with get_execution_scope(job):
                    context = dict(job.env.context)
                    json.dumps(context)  # safety
                    futures = {
                        self.pool.submit(
                            self._worker_execute, subjob.id, context,
                        ): subjob
                        for subjob in job.pending_subjobs
                    }

                    failures = []
                    for future in as_completed(futures):
                        subjob = futures[future]
                        try:
                            future.result()
                        except KeyboardInterrupt:
                            raise  # Will be caught at CLI level
                        except Exception as exc:  # noqa: BLE001
                            exc.add_note(job.env._("in Job %s", subjob.parent_path[:-1]))
                            failures.append((subjob, exc))

                    if failures:
                        raise ExceptionGroup(
                            job.env._("%(count)s parallel job(s) failed", count=len(failures)),
                            [exc for _, exc in failures],
                        )
            else:
                self._execute_with_retry(job)


def start_populate(session: Session, *, profile: bool = False):
    """Execute a single populate session.

    This function is intentionally kept outside the ``populate.session`` model
    API so it can only be reached by trusted Python callers, such as the
    populate CLI.

    If the session was previously interrupted, only pending jobs are executed.

    :param session: Singleton ``populate.session`` to run.
    :param profile: Whether to save profiler entries for this invocation.
    """

    # We do not allow starting multiple sessions at once
    session.ensure_one()
    if session.is_done:
        raise UserError(session.env._(
            "The session %(session_id)s is already done. Create a new session.",
            session_id=session.id,
        ))

    assert session.job_ids, "A created session should have jobs instantiated"

    if profile:
        profile_session = profiler.make_session(get_profile_session_name(session))
        session = session.with_context(**{POPULATE_PROFILE_SESSION_KEY: profile_session})

    try:
        with populate_session_lock(session):
            if session.is_parallel:
                if not has_platform_enabled_multiprocessing():
                    raise RuntimeError(session.env._(
                        "The multiprocessing feature of the populate module has been disabled at the platform level.",
                    ))
                if modules.module.current_test:
                    raise RuntimeError(session.env._("Cannot run a parallel session during tests."))

                executor = ParallelExecutor(session)
            else:
                executor = SequentialExecutor(session)

            with executor:
                executor.execute(session.pending_jobs)

    except LockError as exc:
        raise UserError(session.env._("Session %(session_id)s is already running.", session_id=session.id)) from exc


@contextmanager
def populate_session_lock(session: Session):
    """Acquire the advisory lock that prevents concurrent execution of a session.

    :param session: Singleton session to protect.
    :return: Context manager that releases the lock on exit.
    :raise LockError: If another transaction already holds the session lock.
    """
    session.ensure_one()
    lock_key = session._running_lock_key()
    if not session.env.execute_query(SQL(
        'SELECT pg_try_advisory_lock(hashtext(%s), %s)',
        *lock_key,
    ))[0][0]:
        raise LockError(session.env._("Cannot grab the advisory lock on the session %s.", session.id))

    try:
        yield
    finally:
        session.env.execute_query(SQL(
            'SELECT pg_advisory_unlock(hashtext(%s), %s)',
            *lock_key,
        ))
