# Copyright 2013-2020 Camptocamp
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

import hashlib
import inspect
import logging
import os
import sys
import uuid
import weakref
from datetime import datetime, timedelta
from functools import total_ordering
from random import randint

import odoo

from .exception import FailedJobError, NoSuchJobError, RetryableJobError

WAIT_DEPENDENCIES = "wait_dependencies"
PENDING = "pending"
ENQUEUED = "enqueued"
CANCELLED = "cancelled"
DONE = "done"
STARTED = "started"
FAILED = "failed"

STATES = [
    (WAIT_DEPENDENCIES, "Wait Dependencies"),
    (PENDING, "Pending"),
    (ENQUEUED, "Enqueued"),
    (STARTED, "Started"),
    (DONE, "Done"),
    (CANCELLED, "Cancelled"),
    (FAILED, "Failed"),
]

DEFAULT_PRIORITY = 10  # used by the PriorityQueue to sort the jobs
DEFAULT_MAX_RETRIES = 5
RETRY_INTERVAL = 10 * 60  # seconds

_logger = logging.getLogger(__name__)


# TODO remove in 15.0 or 16.0, used to keep compatibility as the
# class has been moved in 'delay'.
def DelayableRecordset(*args, **kwargs):
    # prevent circular import
    from .delay import DelayableRecordset as dr

    _logger.warning(
        "DelayableRecordset moved from the queue_job.job"
        " to the queue_job.delay python module"
    )
    return dr(*args, **kwargs)


def identity_exact(job_):
    """Identity function using the model, method and all arguments as key

    When used, this identity key will have the effect that when a job should be
    created and a pending job with the exact same recordset and arguments, the
    second will not be created.

    It should be used with the ``identity_key`` argument:

    .. python::

        from odoo.addons.queue_job.job import identity_exact

        # [...]
            delayable = self.with_delay(identity_key=identity_exact)
            delayable.export_record(force=True)

    Alternative identity keys can be built using the various fields of the job.
    For example, you could compute a hash using only some arguments of
    the job.

    .. python::

        def identity_example(job_):
            hasher = hashlib.sha1()
            hasher.update(job_.model_name)
            hasher.update(job_.method_name)
            hasher.update(str(sorted(job_.recordset.ids)))
            hasher.update(str(job_.args[1]))
            hasher.update(str(job_.kwargs.get('foo', '')))
            return hasher.hexdigest()

    Usually you will probably always want to include at least the name of the
    model and method.
    """
    hasher = identity_exact_hasher(job_)
    return hasher.hexdigest()


def identity_exact_hasher(job_):
    """Prepare hasher object for identity_exact."""
    hasher = hashlib.sha1()
    hasher.update(job_.model_name.encode("utf-8"))
    hasher.update(job_.method_name.encode("utf-8"))
    hasher.update(str(sorted(job_.recordset.ids)).encode("utf-8"))
    hasher.update(str(job_.args).encode("utf-8"))
    hasher.update(str(sorted(job_.kwargs.items())).encode("utf-8"))
    return hasher


@total_ordering
class Job(object):
    """A Job is a task to execute. It is the in-memory representation of a job.

    Jobs are stored in the ``queue.job`` Odoo Model, but they are handled
    through this class.

    .. attribute:: uuid

        Id (UUID) of the job.

    .. attribute:: graph_uuid

        Shared UUID of the job's graph. Empty if the job is a single job.

    .. attribute:: state

        State of the job, can pending, enqueued, started, done or failed.
        The start state is pending and the final state is done.

    .. attribute:: retry

        The current try, starts at 0 and each time the job is executed,
        it increases by 1.

    .. attribute:: max_retries

        The maximum number of retries allowed before the job is
        considered as failed.

    .. attribute:: args

        Arguments passed to the function when executed.

    .. attribute:: kwargs

        Keyword arguments passed to the function when executed.

    .. attribute:: description

        Human description of the job.

    .. attribute:: func

        The python function itself.

    .. attribute:: model_name

        Odoo model on which the job will run.

    .. attribute:: priority

        Priority of the job, 0 being the higher priority.

    .. attribute:: date_created

        Date and time when the job was created.

    .. attribute:: date_enqueued

        Date and time when the job was enqueued.

    .. attribute:: date_started

        Date and time when the job was started.

    .. attribute:: date_done

        Date and time when the job was done.

    .. attribute:: result

        A description of the result (for humans).

    .. attribute:: exc_name

        Exception error name when the job failed.

    .. attribute:: exc_message

        Exception error message when the job failed.

    .. attribute:: exc_info

        Exception information (traceback) when the job failed.

    .. attribute:: user_id

        Odoo user id which created the job

    .. attribute:: eta

        Estimated Time of Arrival of the job. It will not be executed
        before this date/time.

    .. attribute:: recordset

        Model recordset when we are on a delayed Model method

    .. attribute::channel

        The complete name of the channel to use to process the job. If
        provided it overrides the one defined on the job's function.

    .. attribute::identity_key

        A key referencing the job, multiple job with the same key will not
        be added to a channel if the existing job with the same key is not yet
        started or executed.

    """

    @classmethod
    def load(cls, env, job_uuid):
        """Read a single job from the Database

        Raise an error if the job is not found.
        """
        stored = cls.db_records_from_uuids(env, [job_uuid])
        if not stored:
            raise NoSuchJobError(
                "Job %s does no longer exist in the storage." % job_uuid
            )
        return cls._load_from_db_record(stored)

    @classmethod
    def load_many(cls, env, job_uuids):
        """Read jobs in batch from the Database

        Jobs not found are ignored.
        """
        recordset = cls.db_records_from_uuids(env, job_uuids)
        return {cls._load_from_db_record(record) for record in recordset}

    @classmethod
    def _load_from_db_record(cls, job_db_record):
        stored = job_db_record

        args = stored.args
        kwargs = stored.kwargs
        method_name = stored.method_name

        recordset = stored.records
        method = getattr(recordset, method_name)

        eta = None
        if stored.eta:
            eta = stored.eta

        job_ = cls(
            method,
            args=args,
            kwargs=kwargs,
            priority=stored.priority,
            eta=eta,
            job_uuid=stored.uuid,
            description=stored.name,
            channel=stored.channel,
            identity_key=stored.identity_key,
        )

        if stored.date_created:
            job_.date_created = stored.date_created

        if stored.date_enqueued:
            job_.date_enqueued = stored.date_enqueued

        if stored.date_started:
            job_.date_started = stored.date_started

        if stored.date_done:
            job_.date_done = stored.date_done

        if stored.date_cancelled:
            job_.date_cancelled = stored.date_cancelled

        job_.state = stored.state
        job_.graph_uuid = stored.graph_uuid if stored.graph_uuid else None
        job_.result = stored.result if stored.result else None
        job_.exc_info = stored.exc_info if stored.exc_info else None
        job_.retry = stored.retry
        job_.max_retries = stored.max_retries
        if stored.company_id:
            job_.company_id = stored.company_id.id
        job_.identity_key = stored.identity_key
        job_.worker_pid = stored.worker_pid

        job_.__depends_on_uuids.update(stored.dependencies.get("depends_on", []))
        job_.__reverse_depends_on_uuids.update(
            stored.dependencies.get("reverse_depends_on", [])
        )
        return job_

    def job_record_with_same_identity_key(self):
        """Check if a job to be executed with the same key exists."""
        existing = (
            self.env["queue.job"]
            .sudo()
            .search(
                [
                    ("identity_key", "=", self.identity_key),
                    ("state", "in", [WAIT_DEPENDENCIES, PENDING, ENQUEUED]),
                ],
                limit=1,
            )
        )
        return existing

    # TODO to deprecate (not called anymore)
    @classmethod
    def enqueue(
        cls,
        func,
        args=None,
        kwargs=None,
        priority=None,
        eta=None,
        max_retries=None,
        description=None,
        channel=None,
        identity_key=None,
    ):
        """Create a Job and enqueue it in the queue. Return the job uuid.

        This expects the arguments specific to the job to be already extracted
        from the ones to pass to the job function.

        If the identity key is the same than the one in a pending job,
        no job is created and the existing job is returned

        """
        new_job = cls(
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            eta=eta,
            max_retries=max_retries,
            description=description,
            channel=channel,
            identity_key=identity_key,
        )
        return new_job._enqueue_job()

    # TODO to deprecate (not called anymore)
    def _enqueue_job(self):
        if self.identity_key:
            existing = self.job_record_with_same_identity_key()
            if existing:
                _logger.debug(
                    "a job has not been enqueued due to having "
                    "the same identity key (%s) than job %s",
                    self.identity_key,
                    existing.uuid,
                )
                return Job._load_from_db_record(existing)
        self.store()
        _logger.debug(
            "enqueued %s:%s(*%r, **%r) with uuid: %s",
            self.recordset,
            self.method_name,
            self.args,
            self.kwargs,
            self.uuid,
        )
        return self

    @staticmethod
    def db_record_from_uuid(env, job_uuid):
        # TODO remove in 15.0 or 16.0
        _logger.debug("deprecated, use 'db_records_from_uuids")
        return Job.db_records_from_uuids(env, [job_uuid])

    @staticmethod
    def db_records_from_uuids(env, job_uuids):
        model = env["queue.job"].sudo()
        record = model.search([("uuid", "in", tuple(job_uuids))])
        return record.with_env(env).sudo()

    def __init__(
        self,
        func,
        args=None,
        kwargs=None,
        priority=None,
        eta=None,
        job_uuid=None,
        max_retries=None,
        description=None,
        channel=None,
        identity_key=None,
    ):
        """Create a Job

        :param func: function to execute
        :type func: function
        :param args: arguments for func
        :type args: tuple
        :param kwargs: keyworkd arguments for func
        :type kwargs: dict
        :param priority: priority of the job,
                         the smaller is the higher priority
        :type priority: int
        :param eta: the job can be executed only after this datetime
                           (or now + timedelta)
        :type eta: datetime or timedelta
        :param job_uuid: UUID of the job
        :param max_retries: maximum number of retries before giving up and set
            the job state to 'failed'. A value of 0 means infinite retries.
        :param description: human description of the job. If None, description
            is computed from the function doc or name
        :param channel: The complete channel name to use to process the job.
        :param identity_key: A hash to uniquely identify a job, or a function
                             that returns this hash (the function takes the job
                             as argument)
        """
        if args is None:
            args = ()
        if isinstance(args, list):
            args = tuple(args)
        assert isinstance(args, tuple), "%s: args are not a tuple" % args
        if kwargs is None:
            kwargs = {}

        assert isinstance(kwargs, dict), "%s: kwargs are not a dict" % kwargs

        if not _is_model_method(func):
            raise TypeError("Job accepts only methods of Models")

        recordset = func.__self__
        env = recordset.env
        self.method_name = func.__name__
        self.recordset = recordset

        self.env = env
        self.job_model = self.env["queue.job"]
        self.job_model_name = "queue.job"

        self.job_config = (
            self.env["queue.job.function"].sudo().job_config(self.job_function_name)
        )

        self.state = PENDING

        self.retry = 0
        if max_retries is None:
            self.max_retries = DEFAULT_MAX_RETRIES
        else:
            self.max_retries = max_retries

        self._uuid = job_uuid
        self.graph_uuid = None

        self.args = args
        self.kwargs = kwargs

        self.__depends_on_uuids = set()
        self.__reverse_depends_on_uuids = set()
        self._depends_on = set()
        self._reverse_depends_on = weakref.WeakSet()

        self.priority = priority
        if self.priority is None:
            self.priority = DEFAULT_PRIORITY

        self.date_created = datetime.now()
        self._description = description

        if isinstance(identity_key, str):
            self._identity_key = identity_key
            self._identity_key_func = None
        else:
            # we'll compute the key on the fly when called
            # from the function
            self._identity_key = None
            self._identity_key_func = identity_key

        self.date_enqueued = None
        self.date_started = None
        self.date_done = None
        self.date_cancelled = None

        self.result = None
        self.exc_name = None
        self.exc_message = None
        self.exc_info = None

        if "company_id" in env.context:
            company_id = env.context["company_id"]
        else:
            company_id = env.company.id
        self.company_id = company_id
        self._eta = None
        self.eta = eta
        self.channel = channel
        self.worker_pid = None

    def add_depends(self, jobs):
        if self in jobs:
            raise ValueError("job cannot depend on itself")
        self.__depends_on_uuids |= {j.uuid for j in jobs}
        self._depends_on.update(jobs)
        for parent in jobs:
            parent.__reverse_depends_on_uuids.add(self.uuid)
            parent._reverse_depends_on.add(self)
        if any(j.state != DONE for j in jobs):
            self.state = WAIT_DEPENDENCIES

    def perform(self):
        """Execute the job.

        The job is executed with the user which has initiated it.
        """
        self.retry += 1
        try:
            self.result = self.func(*tuple(self.args), **self.kwargs)
        except RetryableJobError as err:
            if err.ignore_retry:
                self.retry -= 1
                raise
            elif not self.max_retries:  # infinite retries
                raise
            elif self.retry >= self.max_retries:
                type_, value, traceback = sys.exc_info()
                # change the exception type but keep the original
                # traceback and message:
                # http://blog.ianbicking.org/2007/09/12/re-raising-exceptions/
                new_exc = FailedJobError(
                    "Max. retries (%d) reached: %s" % (self.max_retries, value or type_)
                )
                raise new_exc from err
            raise

        return self.result

    def enqueue_waiting(self):
        sql = """
            UPDATE queue_job
            SET state = %s
            FROM (
            SELECT child.id, array_agg(parent.state) as parent_states
            FROM queue_job job
            JOIN LATERAL
              json_array_elements_text(
                  job.dependencies::json->'reverse_depends_on'
              ) child_deps ON true
            JOIN queue_job child
            ON child.graph_uuid = job.graph_uuid
            AND child.uuid = child_deps
            JOIN LATERAL
                json_array_elements_text(
                  child.dependencies::json->'depends_on'
                ) parent_deps ON true
            JOIN queue_job parent
            ON parent.graph_uuid = job.graph_uuid
            AND parent.uuid = parent_deps
            WHERE job.uuid = %s
            GROUP BY child.id
            ) jobs
            WHERE
            queue_job.id = jobs.id
            AND %s = ALL(jobs.parent_states)
            AND state = %s;
        """
        self.env.cr.execute(sql, (PENDING, self.uuid, DONE, WAIT_DEPENDENCIES))
        self.env["queue.job"].invalidate_model(["state"])

    def store(self):
        """Store the Job"""
        job_model = self.env["queue.job"]
        # The sentinel is used to prevent edition sensitive fields (such as
        # method_name) from RPC methods.
        edit_sentinel = job_model.EDIT_SENTINEL

        db_record = self.db_record()
        if db_record:
            db_record.with_context(_job_edit_sentinel=edit_sentinel).write(
                self._store_values()
            )
        else:
            job_model.with_context(_job_edit_sentinel=edit_sentinel).sudo().create(
                self._store_values(create=True)
            )

    def _store_values(self, create=False):
        vals = {
            "state": self.state,
            "priority": self.priority,
            "retry": self.retry,
            "max_retries": self.max_retries,
            "exc_name": self.exc_name,
            "exc_message": self.exc_message,
            "exc_info": self.exc_info,
            "company_id": self.company_id,
            "result": str(self.result) if self.result else False,
            "date_enqueued": False,
            "date_started": False,
            "date_done": False,
            "exec_time": False,
            "date_cancelled": False,
            "eta": False,
            "identity_key": False,
            "worker_pid": self.worker_pid,
            "graph_uuid": self.graph_uuid,
        }

        if self.date_enqueued:
            vals["date_enqueued"] = self.date_enqueued
        if self.date_started:
            vals["date_started"] = self.date_started
        if self.date_done:
            vals["date_done"] = self.date_done
        if self.exec_time:
            vals["exec_time"] = self.exec_time
        if self.date_cancelled:
            vals["date_cancelled"] = self.date_cancelled
        if self.eta:
            vals["eta"] = self.eta
        if self.identity_key:
            vals["identity_key"] = self.identity_key

        dependencies = {
            "depends_on": [parent.uuid for parent in self.depends_on],
            "reverse_depends_on": [
                children.uuid for children in self.reverse_depends_on
            ],
        }
        vals["dependencies"] = dependencies

        if create:
            vals.update(
                {
                    "user_id": self.env.uid,
                    "channel": self.channel,
                    # The following values must never be modified after the
                    # creation of the job
                    "uuid": self.uuid,
                    "name": self.description,
                    "func_string": self.func_string,
                    "date_created": self.date_created,
                    "model_name": self.recordset._name,
                    "method_name": self.method_name,
                    "job_function_id": self.job_config.job_function_id,
                    "channel_method_name": self.job_function_name,
                    "records": self.recordset,
                    "args": self.args,
                    "kwargs": self.kwargs,
                }
            )

        vals_from_model = self._store_values_from_model()
        # Sanitize values: make sure you cannot screw core values
        vals_from_model = {k: v for k, v in vals_from_model.items() if k not in vals}
        vals.update(vals_from_model)
        return vals

    def _store_values_from_model(self):
        vals = {}
        value_handlers_candidates = (
            "_job_store_values_for_" + self.method_name,
            "_job_store_values",
        )
        for candidate in value_handlers_candidates:
            handler = getattr(self.recordset, candidate, None)
            if handler is not None:
                vals = handler(self)
        return vals

    @property
    def func_string(self):
        model = repr(self.recordset)
        args = [repr(arg) for arg in self.args]
        kwargs = ["{}={!r}".format(key, val) for key, val in self.kwargs.items()]
        all_args = ", ".join(args + kwargs)
        return "{}.{}({})".format(model, self.method_name, all_args)

    def __eq__(self, other):
        return self.uuid == other.uuid

    def __hash__(self):
        return self.uuid.__hash__()

    def sorting_key(self):
        return self.eta, self.priority, self.date_created, self.seq

    def __lt__(self, other):
        if self.eta and not other.eta:
            return True
        elif not self.eta and other.eta:
            return False
        return self.sorting_key() < other.sorting_key()

    def db_record(self):
        return self.db_records_from_uuids(self.env, [self.uuid])

    @property
    def func(self):
        recordset = self.recordset.with_context(job_uuid=self.uuid)
        return getattr(recordset, self.method_name)

    @property
    def job_function_name(self):
        func_model = self.env["queue.job.function"].sudo()
        return func_model.job_function_name(self.recordset._name, self.method_name)

    @property
    def identity_key(self):
        if self._identity_key is None:
            if self._identity_key_func:
                self._identity_key = self._identity_key_func(self)
        return self._identity_key

    @identity_key.setter
    def identity_key(self, value):
        if isinstance(value, str):
            self._identity_key = value
            self._identity_key_func = None
        else:
            # we'll compute the key on the fly when called
            # from the function
            self._identity_key = None
            self._identity_key_func = value

    @property
    def depends_on(self):
        if not self._depends_on:
            self._depends_on = Job.load_many(self.env, self.__depends_on_uuids)
        return self._depends_on

    @property
    def reverse_depends_on(self):
        if not self._reverse_depends_on:
            self._reverse_depends_on = Job.load_many(
                self.env, self.__reverse_depends_on_uuids
            )
        return set(self._reverse_depends_on)

    @property
    def description(self):
        if self._description:
            return self._description
        elif self.func.__doc__:
            return self.func.__doc__.splitlines()[0].strip()
        else:
            return "{}.{}".format(self.model_name, self.func.__name__)

    @property
    def uuid(self):
        """Job ID, this is an UUID"""
        if self._uuid is None:
            self._uuid = str(uuid.uuid4())
        return self._uuid

    @property
    def model_name(self):
        return self.recordset._name

    @property
    def user_id(self):
        return self.recordset.env.uid

    @property
    def eta(self):
        return self._eta

    @eta.setter
    def eta(self, value):
        if not value:
            self._eta = None
        elif isinstance(value, timedelta):
            self._eta = datetime.now() + value
        elif isinstance(value, int):
            self._eta = datetime.now() + timedelta(seconds=value)
        else:
            self._eta = value

    @property
    def channel(self):
        return self._channel or self.job_config.channel

    @channel.setter
    def channel(self, value):
        self._channel = value

    @property
    def exec_time(self):
        if self.date_done and self.date_started:
            return (self.date_done - self.date_started).total_seconds()
        return None

    def set_pending(self, result=None, reset_retry=True):
        if any(j.state != DONE for j in self.depends_on):
            self.state = WAIT_DEPENDENCIES
        else:
            self.state = PENDING
        self.date_enqueued = None
        self.date_started = None
        self.date_done = None
        self.worker_pid = None
        self.date_cancelled = None
        if reset_retry:
            self.retry = 0
        if result is not None:
            self.result = result

    def set_enqueued(self):
        self.state = ENQUEUED
        self.date_enqueued = datetime.now()
        self.date_started = None
        self.worker_pid = None

    def set_started(self):
        self.state = STARTED
        self.date_started = datetime.now()
        self.worker_pid = os.getpid()

    def set_done(self, result=None):
        self.state = DONE
        self.exc_name = None
        self.exc_info = None
        self.date_done = datetime.now()
        if result is not None:
            self.result = result

    def set_cancelled(self, result=None):
        self.state = CANCELLED
        self.date_cancelled = datetime.now()
        if result is not None:
            self.result = result

    def set_failed(self, **kw):
        self.state = FAILED
        for k, v in kw.items():
            if v is not None:
                setattr(self, k, v)

    def __repr__(self):
        return "<Job %s, priority:%d>" % (self.uuid, self.priority)

    def _get_retry_seconds(self, seconds=None):
        retry_pattern = self.job_config.retry_pattern
        if not seconds and retry_pattern:
            # ordered from higher to lower count of retries
            patt = sorted(retry_pattern.items(), key=lambda t: t[0])
            seconds = RETRY_INTERVAL
            for retry_count, postpone_seconds in patt:
                if self.retry >= retry_count:
                    seconds = postpone_seconds
                else:
                    break
        elif not seconds:
            seconds = RETRY_INTERVAL
        if isinstance(seconds, (list, tuple)):
            seconds = randint(seconds[0], seconds[1])
        return seconds

    def postpone(self, result=None, seconds=None):
        """Postpone the job

        Write an estimated time arrival to n seconds
        later than now. Used when an retryable exception
        want to retry a job later.
        """
        eta_seconds = self._get_retry_seconds(seconds)
        self.eta = timedelta(seconds=eta_seconds)
        self.exc_name = None
        self.exc_info = None
        if result is not None:
            self.result = result

    def related_action(self):
        record = self.db_record()
        if not self.job_config.related_action_enable:
            return None

        funcname = self.job_config.related_action_func_name
        if not funcname:
            funcname = record._default_related_action
        if not isinstance(funcname, str):
            raise ValueError(
                "related_action must be the name of the "
                "method on queue.job as string"
            )
        action = getattr(record, funcname)
        action_kwargs = self.job_config.related_action_kwargs
        return action(**action_kwargs)


def _is_model_method(func):
    return inspect.ismethod(func) and isinstance(
        func.__self__.__class__, odoo.models.MetaModel
    )
