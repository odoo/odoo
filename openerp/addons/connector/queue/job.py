# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import inspect
import functools
import logging
import uuid
import sys
from datetime import datetime, timedelta, MINYEAR
from cPickle import dumps, UnpicklingError, Unpickler
from cStringIO import StringIO

import openerp
from openerp.tools.translate import _

from ..exception import (NotReadableJobError,
                         NoSuchJobError,
                         FailedJobError,
                         RetryableJobError)

PENDING = 'pending'
ENQUEUED = 'enqueued'
DONE = 'done'
STARTED = 'started'
FAILED = 'failed'

STATES = [(PENDING, 'Pending'),
          (ENQUEUED, 'Enqueued'),
          (STARTED, 'Started'),
          (DONE, 'Done'),
          (FAILED, 'Failed')]

DEFAULT_PRIORITY = 10  # used by the PriorityQueue to sort the jobs
DEFAULT_MAX_RETRIES = 5
RETRY_INTERVAL = 10 * 60  # seconds

_logger = logging.getLogger(__name__)


_UNPICKLE_WHITELIST = set()


def whitelist_unpickle_global(fn_or_class):
    """ Allow a function or class to be used in jobs

    By default, the only types allowed to be used in job arguments are:

    * the builtins: str/unicode, int/long, float, bool, tuple, list, dict, None
    * the pre-registered: datetime.datetime datetime.timedelta

    If you need to use an argument in a job which is not in this whitelist,
    you can add it by using::

        whitelist_unpickle_global(fn_or_class_to_register)

    """
    _UNPICKLE_WHITELIST.add(fn_or_class)


# register common types that might be used in job arguments
whitelist_unpickle_global(datetime)
whitelist_unpickle_global(timedelta)


def _unpickle(pickled):
    """ Unpickles a string and catch all types of errors it can throw,
    to raise only NotReadableJobError in case of error.

    OpenERP stores the text fields as 'utf-8', so we specify the encoding.

    `loads()` may raises many types of exceptions (AttributeError,
    IndexError, TypeError, KeyError, ...). They are all catched and
    raised as `NotReadableJobError`).

    Pickle could be exploited by an attacker who would write a value in a job
    that would run arbitrary code when unpickled. This is why we set a custom
    ``find_global`` method on the ``Unpickler``, only jobs and a whitelist of
    classes/functions are allowed to be unpickled (plus the builtins types).
    """
    def restricted_find_global(mod_name, fn_name):
        __import__(mod_name)
        mod = sys.modules[mod_name]
        fn = getattr(mod, fn_name)
        if not (fn in JOB_REGISTRY or fn in _UNPICKLE_WHITELIST):
            raise UnpicklingError(
                '{}.{} is not allowed in jobs'.format(mod_name, fn_name)
            )
        return fn

    unpickler = Unpickler(StringIO(pickled))
    unpickler.find_global = restricted_find_global
    try:
        unpickled = unpickler.load()
    except (StandardError, UnpicklingError):
        raise NotReadableJobError('Could not unpickle.', pickled)
    return unpickled


class JobStorage(object):
    """ Interface for the storage of jobs """

    def store(self, job_):
        """ Store a job """
        raise NotImplementedError

    def load(self, job_uuid):
        """ Read the job's data from the storage """
        raise NotImplementedError

    def exists(self, job_uuid):
        """Returns if a job still exists in the storage."""
        raise NotImplementedError


class OpenERPJobStorage(JobStorage):
    """ Store a job on OpenERP """

    _job_model_name = 'queue.job'

    def __init__(self, session):
        super(OpenERPJobStorage, self).__init__()
        self.session = session
        self.job_model = self.session.env[self._job_model_name]
        assert self.job_model is not None, (
            "Model %s not found" % self._job_model_name)

    def enqueue(self, func, model_name=None, args=None, kwargs=None,
                priority=None, eta=None, max_retries=None, description=None):
        """Create a Job and enqueue it in the queue. Return the job uuid.

        This expects the arguments specific to the job to be already extracted
        from the ones to pass to the job function.

        """
        new_job = Job(func=func, model_name=model_name, args=args,
                      kwargs=kwargs, priority=priority, eta=eta,
                      max_retries=max_retries, description=description)
        new_job.user_id = self.session.uid
        if 'company_id' in self.session.context:
            company_id = self.session.context['company_id']
        else:
            company_model = self.session.env['res.company']
            company_model = company_model.sudo(new_job.user_id)
            company_id = company_model._company_default_get(
                object='queue.job',
                field='company_id').id
        new_job.company_id = company_id
        self.store(new_job)
        return new_job.uuid

    def enqueue_resolve_args(self, func, *args, **kwargs):
        """Create a Job and enqueue it in the queue. Return the job uuid."""
        priority = kwargs.pop('priority', None)
        eta = kwargs.pop('eta', None)
        model_name = kwargs.pop('model_name', None)
        max_retries = kwargs.pop('max_retries', None)
        description = kwargs.pop('description', None)

        return self.enqueue(func, model_name=model_name,
                            args=args, kwargs=kwargs,
                            priority=priority,
                            max_retries=max_retries,
                            eta=eta,
                            description=description)

    def exists(self, job_uuid):
        """Returns if a job still exists in the storage."""
        return bool(self.db_record_from_uuid(job_uuid))

    def db_record_from_uuid(self, job_uuid):
        model = self.job_model.sudo().with_context(active_test=False)
        record = model.search([('uuid', '=', job_uuid)], limit=1)
        if record:
            return record.with_env(self.job_model.env)

    def db_record(self, job_):
        return self.db_record_from_uuid(job_.uuid)

    def store(self, job_):
        """ Store the Job """
        vals = {'state': job_.state,
                'priority': job_.priority,
                'retry': job_.retry,
                'max_retries': job_.max_retries,
                'exc_info': job_.exc_info,
                'user_id': job_.user_id or self.session.uid,
                'company_id': job_.company_id,
                'result': unicode(job_.result) if job_.result else False,
                'date_enqueued': False,
                'date_started': False,
                'date_done': False,
                'eta': False,
                'func_name': job_.func_name,
                }

        dt_to_string = openerp.fields.Datetime.to_string
        if job_.date_enqueued:
            vals['date_enqueued'] = dt_to_string(job_.date_enqueued)
        if job_.date_started:
            vals['date_started'] = dt_to_string(job_.date_started)
        if job_.date_done:
            vals['date_done'] = dt_to_string(job_.date_done)
        if job_.eta:
            vals['eta'] = dt_to_string(job_.eta)

        if job_.canceled:
            vals['active'] = False

        db_record = self.db_record(job_)
        if db_record:
            db_record.write(vals)
        else:
            date_created = dt_to_string(job_.date_created)
            vals.update({'uuid': job_.uuid,
                         'name': job_.description,
                         'func_string': job_.func_string,
                         'date_created': date_created,
                         'model_name': (job_.model_name if job_.model_name
                                        else False),
                         })

            vals['func'] = dumps((job_.func_name,
                                  job_.args,
                                  job_.kwargs))

            self.job_model.sudo().create(vals)

    def load(self, job_uuid):
        """ Read a job from the Database"""
        stored = self.db_record_from_uuid(job_uuid)
        if not stored:
            raise NoSuchJobError(
                'Job %s does no longer exist in the storage.' % job_uuid)

        func = _unpickle(stored.func)

        (func_name, args, kwargs) = func

        dt_from_string = openerp.fields.Datetime.from_string
        eta = None
        if stored.eta:
            eta = dt_from_string(stored.eta)

        job_ = Job(func=func_name, args=args, kwargs=kwargs,
                   priority=stored.priority, eta=eta, job_uuid=stored.uuid,
                   description=stored.name)

        if stored.date_created:
            job_.date_created = dt_from_string(stored.date_created)

        if stored.date_enqueued:
            job_.date_enqueued = dt_from_string(stored.date_enqueued)

        if stored.date_started:
            job_.date_started = dt_from_string(stored.date_started)

        if stored.date_done:
            job_.date_done = dt_from_string(stored.date_done)

        job_.state = stored.state
        job_.result = stored.result if stored.result else None
        job_.exc_info = stored.exc_info if stored.exc_info else None
        job_.user_id = stored.user_id.id if stored.user_id else None
        job_.canceled = not stored.active
        job_.model_name = stored.model_name if stored.model_name else None
        job_.retry = stored.retry
        job_.max_retries = stored.max_retries
        if stored.company_id:
            job_.company_id = stored.company_id.id
        return job_


class Job(object):
    """ A Job is a task to execute.

    .. attribute:: uuid

        Id (UUID) of the job.

    .. attribute:: state

        State of the job, can pending, enqueued, started, done or failed.
        The start state is pending and the final state is done.

    .. attribute:: retry

        The current try, starts at 0 and each time the job is executed,
        it increases by 1.

    .. attribute:: max_retries

        The maximum number of retries allowed before the job is
        considered as failed.

    .. attribute:: func_name

        Name of the function (in the form module.function_name).

    .. attribute:: args

        Arguments passed to the function when executed.

    .. attribute:: kwargs

        Keyword arguments passed to the function when executed.

    .. attribute:: func_string

        Full string representing the function to be executed,
        ie. module.function(args, kwargs)

    .. attribute:: description

        Human description of the job.

    .. attribute:: func

        The python function itself.

    .. attribute:: model_name

        OpenERP model on which the job will run.

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

    .. attribute:: exc_info

        Exception information (traceback) when the job failed.

    .. attribute:: user_id

        OpenERP user id which created the job

    .. attribute:: eta

        Estimated Time of Arrival of the job. It will not be executed
        before this date/time.

    .. attribute:: canceled

        True if the job has been canceled.

    """

    def __init__(self, func=None, model_name=None,
                 args=None, kwargs=None, priority=None,
                 eta=None, job_uuid=None, max_retries=None,
                 description=None):
        """ Create a Job

        :param func: function to execute
        :type func: function
        :param model_name: name of the model targetted by the job
        :type model_name: str
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
        """
        if args is None:
            args = ()
        assert isinstance(args, tuple), "%s: args are not a tuple" % args
        if kwargs is None:
            kwargs = {}

        assert isinstance(kwargs, dict), "%s: kwargs are not a dict" % kwargs
        assert func is not None, "func is required"

        self.state = PENDING

        self.retry = 0
        if max_retries is None:
            self.max_retries = DEFAULT_MAX_RETRIES
        else:
            self.max_retries = max_retries

        self._uuid = job_uuid

        self.func_name = None
        if func:
            if inspect.ismethod(func):
                raise NotImplementedError('Jobs on instances methods are '
                                          'not supported')
            elif inspect.isfunction(func):
                self.func_name = '%s.%s' % (func.__module__, func.__name__)
            elif isinstance(func, basestring):
                self.func_name = func
            else:
                raise TypeError('%s is not a valid function for a job' % func)

        self.model_name = model_name
        # the model name is by convention the second argument of the job
        if self.model_name:
            args = tuple([self.model_name] + list(args))
        self.args = args
        self.kwargs = kwargs

        self.priority = priority
        if self.priority is None:
            self.priority = DEFAULT_PRIORITY

        self.date_created = datetime.now()
        self._description = description
        self.date_enqueued = None
        self.date_started = None
        self.date_done = None

        self.result = None
        self.exc_info = None

        self.user_id = None
        self.company_id = None
        self._eta = None
        self.eta = eta
        self.canceled = False

    def __cmp__(self, other):
        if not isinstance(other, Job):
            raise TypeError("Job.__cmp__(self, other) requires other to be "
                            "a 'Job', not a '%s'" % type(other))
        self_eta = self.eta or datetime(MINYEAR, 1, 1)
        other_eta = other.eta or datetime(MINYEAR, 1, 1)
        return cmp((self_eta, self.priority, self.date_created),
                   (other_eta, other.priority, other.date_created))

    def perform(self, session):
        """ Execute the job.

        The job is executed with the user which has initiated it.

        :param session: session to execute the job
        :type session: ConnectorSession
        """
        assert not self.canceled, "Canceled job"
        with session.change_user(self.user_id):
            self.retry += 1
            try:
                with session.change_context({'job_uuid': self._uuid}):
                    self.result = self.func(session, *self.args, **self.kwargs)
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
                    new_exc = FailedJobError("Max. retries (%d) reached: %s" %
                                             (self.max_retries, value or type_)
                                             )
                    raise new_exc.__class__, new_exc, traceback
                raise
        return self.result

    @property
    def func_string(self):
        if self.func_name is None:
            return None
        args = [repr(arg) for arg in self.args]
        kwargs = ['%s=%r' % (key, val) for key, val
                  in self.kwargs.iteritems()]
        return '%s(%s)' % (self.func_name, ', '.join(args + kwargs))

    @property
    def description(self):
        descr = (self._description or
                 self.func.__doc__ or
                 'Function %s' % self.func.__name__)
        return descr

    @property
    def uuid(self):
        """Job ID, this is an UUID """
        if self._uuid is None:
            self._uuid = unicode(uuid.uuid4())
        return self._uuid

    @property
    def func(self):
        func_name = self.func_name
        if func_name is None:
            return None

        module_name, func_name = func_name.rsplit('.', 1)
        __import__(module_name)
        module = sys.modules[module_name]
        return getattr(module, func_name)

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

    def set_pending(self, result=None, reset_retry=True):
        self.state = PENDING
        self.date_enqueued = None
        self.date_started = None
        if reset_retry:
            self.retry = 0
        if result is not None:
            self.result = result

    def set_enqueued(self):
        self.state = ENQUEUED
        self.date_enqueued = datetime.now()
        self.date_started = None

    def set_started(self):
        self.state = STARTED
        self.date_started = datetime.now()

    def set_done(self, result=None):
        self.state = DONE
        self.exc_info = None
        self.date_done = datetime.now()
        if result is not None:
            self.result = result

    def set_failed(self, exc_info=None):
        self.state = FAILED
        if exc_info is not None:
            self.exc_info = exc_info

    def __repr__(self):
        return '<Job %s, priority:%d>' % (self.uuid, self.priority)

    def cancel(self, msg=None):
        self.canceled = True
        result = msg if msg is not None else _('Canceled. Nothing to do.')
        self.set_done(result=result)

    def _get_retry_seconds(self, seconds=None):
        retry_pattern = self.func.retry_pattern
        if not seconds and retry_pattern:
            # ordered from higher to lower count of retries
            patt = sorted(retry_pattern.iteritems(), key=lambda t: t[0])
            seconds = RETRY_INTERVAL
            for retry_count, postpone_seconds in patt:
                if self.retry >= retry_count:
                    seconds = postpone_seconds
                else:
                    break
        elif not seconds:
            seconds = RETRY_INTERVAL
        return seconds

    def postpone(self, result=None, seconds=None):
        """ Write an estimated time arrival to n seconds
        later than now. Used when an retryable exception
        want to retry a job later. """
        eta_seconds = self._get_retry_seconds(seconds)
        self.eta = timedelta(seconds=eta_seconds)
        self.exc_info = None
        if result is not None:
            self.result = result

    def related_action(self, session):
        if not hasattr(self.func, 'related_action'):
            return None
        return self.func.related_action(session, self)


JOB_REGISTRY = set()


def job(func=None, default_channel='root', retry_pattern=None):
    """ Decorator for jobs.

    Optional argument:

    :param default_channel: the channel wherein the job will be assigned. This
                            channel is set at the installation of the module
                            and can be manually changed later using the views.
    :param retry_pattern: The retry pattern to use for postponing a job.
                          If a job is postponed and there is no eta
                          specified, the eta will be determined from the
                          dict in retry_pattern. When no retry pattern
                          is provided, jobs will be retried after
                          :const:`RETRY_INTERVAL` seconds.
    :type retry_pattern: dict(retry_count,retry_eta_seconds)

    Add a ``delay`` attribute on the decorated function.

    When ``delay`` is called, the function is transformed to a job and
    stored in the OpenERP queue.job model. The arguments and keyword
    arguments given in ``delay`` will be the arguments used by the
    decorated function when it is executed.

    ``retry_pattern`` is a dict where keys are the count of retries and the
    values are the delay to postpone a job.

    The ``delay()`` function of a job takes the following arguments:

    session
      Current :py:class:`~openerp.addons.connector.session.ConnectorSession`

    model_name
      name of the model on which the job has something to do

    *args and **kargs
     Arguments and keyword arguments which will be given to the called
     function once the job is executed. They should be ``pickle-able``.

     There are 5 special and reserved keyword arguments that you can use:

     * priority: priority of the job, the smaller is the higher priority.
                 Default is 10.
     * max_retries: maximum number of retries before giving up and set
                    the job state to 'failed'. A value of 0 means
                    infinite retries. Default is 5.
     * eta: the job can be executed only after this datetime
            (or now + timedelta if a timedelta or integer is given)
     * description : a human description of the job,
                     intended to discriminate job instances
                     (Default is the func.__doc__ or
                      'Function %s' % func.__name__)

    Example:

    .. code-block:: python

        @job
        def export_one_thing(session, model_name, one_thing):
            # work
            # export one_thing

        export_one_thing(session, 'a.model', the_thing_to_export)
        # => normal and synchronous function call

        export_one_thing.delay(session, 'a.model', the_thing_to_export)
        # => the job will be executed as soon as possible

        export_one_thing.delay(session, 'a.model', the_thing_to_export,
                               priority=30, eta=60*60*5)
        # => the job will be executed with a low priority and not before a
        # delay of 5 hours from now

        @job(default_channel='root.subchannel')
        def export_one_thing(session, model_name, one_thing):
            # work
            # export one_thing

        @job(retry_pattern={1: 10 * 60,
                            5: 20 * 60,
                            10: 30 * 60,
                            15: 12 * 60 * 60})
        def retryable_example(session):
            # 5 first retries postponed 10 minutes later
            # retries 5 to 10 postponed 20 minutes later
            # retries 10 to 15 postponed 30 minutes later
            # all subsequent retries postponed 12 hours later
            raise RetryableJobError('Must be retried later')

        retryable_example.delay(session)


    See also: :py:func:`related_action` a related action can be attached
    to a job

    """
    if func is None:
        return functools.partial(job, default_channel=default_channel,
                                 retry_pattern=retry_pattern)

    def delay(session, model_name, *args, **kwargs):
        """Enqueue the function. Return the uuid of the created job."""
        return OpenERPJobStorage(session).enqueue_resolve_args(
            func,
            model_name=model_name,
            *args,
            **kwargs)

    assert default_channel == 'root' or default_channel.startswith('root.'), (
        "The channel path must start by 'root'")
    func.default_channel = default_channel
    assert retry_pattern is None or isinstance(retry_pattern, dict), (
        "retry_pattern must be a dict"
    )
    func.retry_pattern = retry_pattern
    func.delay = delay
    JOB_REGISTRY.add(func)
    return func


def related_action(action=lambda session, job: None, **kwargs):
    """ Attach a *Related Action* to a job.

    A *Related Action* will appear as a button on the OpenERP view.
    The button will execute the action, usually it will open the
    form view of the record related to the job.

    The ``action`` must be a callable that responds to arguments::

        session, job, **kwargs

    Example usage:

    .. code-block:: python

        def related_action_partner(session, job):
            model = job.args[0]
            partner_id = job.args[1]
            # eventually get the real ID if partner_id is a binding ID
            action = {
                'name': _("Partner"),
                'type': 'ir.actions.act_window',
                'res_model': model,
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': partner_id,
            }
            return action

        @job
        @related_action(action=related_action_partner)
        def export_partner(session, model_name, partner_id):
            # ...

    The kwargs are transmitted to the action:

    .. code-block:: python

        def related_action_product(session, job, extra_arg=1):
            assert extra_arg == 2
            model = job.args[0]
            product_id = job.args[1]

        @job
        @related_action(action=related_action_product, extra_arg=2)
        def export_product(session, model_name, product_id):
            # ...

    """
    def decorate(func):
        if kwargs:
            func.related_action = functools.partial(action, **kwargs)
        else:
            func.related_action = action
        return func
    return decorate
