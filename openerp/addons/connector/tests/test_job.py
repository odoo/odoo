# -*- coding: utf-8 -*-

import cPickle
import mock
import unittest
from datetime import datetime, timedelta

from openerp import SUPERUSER_ID, exceptions
import openerp.tests.common as common
from openerp.addons.connector.queue.job import (
    Job,
    JobStorage,
    OpenERPJobStorage,
    job,
    PENDING,
    ENQUEUED,
    DONE,
    STARTED,
    FAILED,
    _unpickle,
    RETRY_INTERVAL,
)
from openerp.addons.connector.session import (
    ConnectorSession,
)
from openerp.addons.connector.exception import (
    FailedJobError,
    NoSuchJobError,
    NotReadableJobError,
    RetryableJobError,
)


def task_b(session, model_name):
    pass


def task_a(session, model_name):
    """ Task description
    """


def dummy_task(session):
    return 'ok'


def dummy_task_args(session, model_name, a, b, c=None):
    return a + b + c


def dummy_task_context(session):
    return session.env.context


def retryable_error_task(session):
    raise RetryableJobError('Must be retried later')


def pickle_forbidden_function(session):
    pass


@job
def pickle_allowed_function(session):
    pass


class TestJobs(unittest.TestCase):
    """ Test Job """

    def setUp(self):
        self.session = mock.MagicMock()

    def test_new_job(self):
        """
        Create a job
        """
        test_job = Job(func=task_a)
        self.assertEqual(test_job.func, task_a)

    def test_priority(self):
        """ The lower the priority number, the higher
        the priority is"""
        job_a = Job(func=task_a, priority=10)
        job_b = Job(func=task_b, priority=5)
        self.assertGreater(job_a, job_b)

    def test_compare_eta(self):
        """ When an `eta` datetime is defined, it should
        be executed after a job without one.
        """
        date = datetime.now() + timedelta(hours=3)
        job_a = Job(func=task_a, priority=10, eta=date)
        job_b = Job(func=task_b, priority=10)
        self.assertGreater(job_a, job_b)

    def test_eta(self):
        """ When an `eta` is datetime, it uses it """
        now = datetime.now()
        job_a = Job(func=task_a, eta=now)
        self.assertEqual(job_a.eta, now)

    def test_eta_integer(self):
        """ When an `eta` is an integer, it adds n seconds up to now """
        datetime_path = 'openerp.addons.connector.queue.job.datetime'
        with mock.patch(datetime_path, autospec=True) as mock_datetime:
            mock_datetime.now.return_value = datetime(2015, 3, 15, 16, 41, 0)
            job_a = Job(func=task_a, eta=60)
            self.assertEqual(job_a.eta, datetime(2015, 3, 15, 16, 42, 0))

    def test_eta_timedelta(self):
        """ When an `eta` is a timedelta, it adds it up to now """
        datetime_path = 'openerp.addons.connector.queue.job.datetime'
        with mock.patch(datetime_path, autospec=True) as mock_datetime:
            mock_datetime.now.return_value = datetime(2015, 3, 15, 16, 41, 0)
            delta = timedelta(hours=3)
            job_a = Job(func=task_a, eta=delta)
            self.assertEqual(job_a.eta, datetime(2015, 3, 15, 19, 41, 0))

    def test_perform(self):
        test_job = Job(func=dummy_task)
        result = test_job.perform(self.session)
        self.assertEqual(result, 'ok')

    def test_perform_args(self):
        test_job = Job(func=dummy_task_args,
                       model_name='res.users',
                       args=('o', 'k'),
                       kwargs={'c': '!'})
        result = test_job.perform(self.session)
        self.assertEqual(result, 'ok!')

    def test_description(self):
        """ If no description is given to the job, it
        should be computed from the function
        """
        # if a doctstring is defined for the function
        # it's used as description
        job_a = Job(func=task_a)
        self.assertEqual(job_a.description, task_a.__doc__)
        # if no docstring, the description is computed
        job_b = Job(func=task_b)
        self.assertEqual(job_b.description, "Function task_b")
        # case when we explicitly specify the description
        description = "My description"
        job_a = Job(func=task_a, description=description)
        self.assertEqual(job_a.description, description)

    def test_retryable_error(self):
        test_job = Job(func=retryable_error_task,
                       max_retries=3)
        self.assertEqual(test_job.retry, 0)
        with self.assertRaises(RetryableJobError):
            test_job.perform(self.session)
        self.assertEqual(test_job.retry, 1)
        with self.assertRaises(RetryableJobError):
            test_job.perform(self.session)
        self.assertEqual(test_job.retry, 2)
        with self.assertRaises(FailedJobError):
            test_job.perform(self.session)
        self.assertEqual(test_job.retry, 3)

    def test_infinite_retryable_error(self):
        test_job = Job(func=retryable_error_task,
                       max_retries=0)
        self.assertEqual(test_job.retry, 0)
        with self.assertRaises(RetryableJobError):
            test_job.perform(self.session)
        self.assertEqual(test_job.retry, 1)

    def test_retry_pattern(self):
        """ When we specify a retry pattern, the eta must follow it"""
        datetime_path = 'openerp.addons.connector.queue.job.datetime'
        test_pattern = {
            1:  60,
            2: 180,
            3:  10,
            5: 300,
        }
        job(retryable_error_task, retry_pattern=test_pattern)
        with mock.patch(datetime_path, autospec=True) as mock_datetime:
            mock_datetime.now.return_value = datetime(2015, 6, 1, 15, 10, 0)
            test_job = Job(func=retryable_error_task,
                           max_retries=0)
            test_job.retry += 1
            test_job.postpone(self.session)
            self.assertEqual(test_job.retry, 1)
            self.assertEqual(test_job.eta, datetime(2015, 6, 1, 15, 11, 0))
            test_job.retry += 1
            test_job.postpone(self.session)
            self.assertEqual(test_job.retry, 2)
            self.assertEqual(test_job.eta, datetime(2015, 6, 1, 15, 13, 0))
            test_job.retry += 1
            test_job.postpone(self.session)
            self.assertEqual(test_job.retry, 3)
            self.assertEqual(test_job.eta, datetime(2015, 6, 1, 15, 10, 10))
            test_job.retry += 1
            test_job.postpone(self.session)
            self.assertEqual(test_job.retry, 4)
            self.assertEqual(test_job.eta, datetime(2015, 6, 1, 15, 10, 10))
            test_job.retry += 1
            test_job.postpone(self.session)
            self.assertEqual(test_job.retry, 5)
            self.assertEqual(test_job.eta, datetime(2015, 6, 1, 15, 15, 00))

    def test_retry_pattern_no_zero(self):
        """ When we specify a retry pattern without 0, uses RETRY_INTERVAL"""
        test_pattern = {
            3: 180,
        }
        job(retryable_error_task, retry_pattern=test_pattern)
        test_job = Job(func=retryable_error_task,
                       max_retries=0)
        test_job.retry += 1
        self.assertEqual(test_job.retry, 1)
        self.assertEqual(test_job._get_retry_seconds(), RETRY_INTERVAL)
        test_job.retry += 1
        self.assertEqual(test_job.retry, 2)
        self.assertEqual(test_job._get_retry_seconds(), RETRY_INTERVAL)
        test_job.retry += 1
        self.assertEqual(test_job.retry, 3)
        self.assertEqual(test_job._get_retry_seconds(), 180)
        test_job.retry += 1
        self.assertEqual(test_job.retry, 4)
        self.assertEqual(test_job._get_retry_seconds(), 180)

    def test_on_method(self):

        class A(object):
            def method(self):
                pass

        with self.assertRaises(NotImplementedError):
            Job(A.method)

    def test_invalid_function(self):
        with self.assertRaises(TypeError):
            Job(1)

    def test_compare_apple_and_orange(self):
        with self.assertRaises(TypeError):
            Job(func=task_a) != 1

    def test_set_pending(self):
        job_a = Job(func=task_a)
        job_a.set_pending(result='test')
        self.assertEquals(job_a.state, PENDING)
        self.assertFalse(job_a.date_enqueued)
        self.assertFalse(job_a.date_started)
        self.assertEquals(job_a.retry, 0)
        self.assertEquals(job_a.result, 'test')

    def test_set_enqueued(self):
        job_a = Job(func=task_a)
        datetime_path = 'openerp.addons.connector.queue.job.datetime'
        with mock.patch(datetime_path, autospec=True) as mock_datetime:
            mock_datetime.now.return_value = datetime(2015, 3, 15, 16, 41, 0)
            job_a.set_enqueued()

        self.assertEquals(job_a.state, ENQUEUED)
        self.assertEquals(job_a.date_enqueued,
                          datetime(2015, 3, 15, 16, 41, 0))
        self.assertFalse(job_a.date_started)

    def test_set_started(self):
        job_a = Job(func=task_a)
        datetime_path = 'openerp.addons.connector.queue.job.datetime'
        with mock.patch(datetime_path, autospec=True) as mock_datetime:
            mock_datetime.now.return_value = datetime(2015, 3, 15, 16, 41, 0)
            job_a.set_started()

        self.assertEquals(job_a.state, STARTED)
        self.assertEquals(job_a.date_started,
                          datetime(2015, 3, 15, 16, 41, 0))

    def test_set_done(self):
        job_a = Job(func=task_a)
        datetime_path = 'openerp.addons.connector.queue.job.datetime'
        with mock.patch(datetime_path, autospec=True) as mock_datetime:
            mock_datetime.now.return_value = datetime(2015, 3, 15, 16, 41, 0)
            job_a.set_done(result='test')

        self.assertEquals(job_a.state, DONE)
        self.assertEquals(job_a.result, 'test')
        self.assertEquals(job_a.date_done,
                          datetime(2015, 3, 15, 16, 41, 0))
        self.assertFalse(job_a.exc_info)

    def test_set_failed(self):
        job_a = Job(func=task_a)
        job_a.set_failed(exc_info='failed test')
        self.assertEquals(job_a.state, FAILED)
        self.assertEquals(job_a.exc_info, 'failed test')

    def test_cancel(self):
        job_a = Job(func=task_a)
        job_a.cancel(msg='test')
        self.assertTrue(job_a.canceled)
        self.assertEquals(job_a.state, DONE)
        self.assertEquals(job_a.result, 'test')

    def test_postpone(self):
        job_a = Job(func=task_a)
        datetime_path = 'openerp.addons.connector.queue.job.datetime'
        with mock.patch(datetime_path, autospec=True) as mock_datetime:
            mock_datetime.now.return_value = datetime(2015, 3, 15, 16, 41, 0)
            job_a.postpone(result='test', seconds=60)

        self.assertEquals(job_a.eta, datetime(2015, 3, 15, 16, 42, 0))
        self.assertEquals(job_a.result, 'test')
        self.assertFalse(job_a.exc_info)

    def test_unpickle(self):
        pickle = ("S'a small cucumber preserved in vinegar, "
                  "brine, or a similar solution.'\np0\n.")
        self.assertEqual(_unpickle(pickle),
                         'a small cucumber preserved in vinegar, '
                         'brine, or a similar solution.')

    def test_unpickle_unsafe(self):
        """ unpickling function not decorated by @job is forbidden """
        pickled = cPickle.dumps(pickle_forbidden_function)
        with self.assertRaises(NotReadableJobError):
            _unpickle(pickled)

    def test_unpickle_safe(self):
        """ unpickling function decorated by @job is allowed """
        pickled = cPickle.dumps(pickle_allowed_function)
        self.assertEqual(_unpickle(pickled), pickle_allowed_function)

    def test_unpickle_whitelist(self):
        """ unpickling function/class that is in the whitelist is allowed """
        arg = datetime(2016, 2, 10)
        pickled = cPickle.dumps(arg)
        self.assertEqual(_unpickle(pickled), arg)

    def test_unpickle_not_readable(self):
        with self.assertRaises(NotReadableJobError):
            self.assertEqual(_unpickle('cucumber'))

    def test_not_implemented_job_storage(self):
        storage = JobStorage()
        job_a = mock.Mock()
        with self.assertRaises(NotImplementedError):
            storage.store(job_a)
            storage.load(job_a)
            storage.exists(job_a)


class TestJobStorage(common.TransactionCase):
    """ Test storage of jobs """

    def setUp(self):
        super(TestJobStorage, self).setUp()
        self.session = ConnectorSession(self.cr, self.uid)
        self.queue_job = self.env['queue.job']

    def test_store(self):
        test_job = Job(func=task_a)
        storage = OpenERPJobStorage(self.session)
        storage.store(test_job)
        stored = self.queue_job.search([('uuid', '=', test_job.uuid)])
        self.assertEqual(len(stored), 1)

    def test_read(self):
        eta = datetime.now() + timedelta(hours=5)
        test_job = Job(func=dummy_task_args,
                       model_name='res.users',
                       args=('o', 'k'),
                       kwargs={'c': '!'},
                       priority=15,
                       eta=eta,
                       description="My description")
        test_job.user_id = 1
        test_job.company_id = self.env.ref("base.main_company").id
        storage = OpenERPJobStorage(self.session)
        storage.store(test_job)
        job_read = storage.load(test_job.uuid)
        self.assertEqual(test_job.uuid, job_read.uuid)
        self.assertEqual(test_job.model_name, job_read.model_name)
        self.assertEqual(test_job.func, job_read.func)
        self.assertEqual(test_job.args, job_read.args)
        self.assertEqual(test_job.kwargs, job_read.kwargs)
        self.assertEqual(test_job.func_name, job_read.func_name)
        self.assertEqual(test_job.func_string, job_read.func_string)
        self.assertEqual(test_job.description, job_read.description)
        self.assertEqual(test_job.state, job_read.state)
        self.assertEqual(test_job.priority, job_read.priority)
        self.assertEqual(test_job.exc_info, job_read.exc_info)
        self.assertEqual(test_job.result, job_read.result)
        self.assertEqual(test_job.user_id, job_read.user_id)
        self.assertEqual(test_job.company_id, job_read.company_id)
        delta = timedelta(seconds=1)  # DB does not keep milliseconds
        self.assertAlmostEqual(test_job.date_created, job_read.date_created,
                               delta=delta)
        self.assertAlmostEqual(test_job.date_started, job_read.date_started,
                               delta=delta)
        self.assertAlmostEqual(test_job.date_enqueued, job_read.date_enqueued,
                               delta=delta)
        self.assertAlmostEqual(test_job.date_done, job_read.date_done,
                               delta=delta)
        self.assertAlmostEqual(test_job.eta, job_read.eta,
                               delta=delta)

        test_date = datetime(2015, 3, 15, 21, 7, 0)
        job_read.date_enqueued = test_date
        job_read.date_started = test_date
        job_read.date_done = test_date
        job_read.canceled = True
        storage.store(job_read)

        job_read = storage.load(test_job.uuid)
        self.assertAlmostEqual(job_read.date_started, test_date,
                               delta=delta)
        self.assertAlmostEqual(job_read.date_enqueued, test_date,
                               delta=delta)
        self.assertAlmostEqual(job_read.date_done, test_date,
                               delta=delta)
        self.assertEqual(job_read.canceled, True)

    def test_job_unlinked(self):
        test_job = Job(func=dummy_task_args,
                       model_name='res.users',
                       args=('o', 'k'),
                       kwargs={'c': '!'})
        storage = OpenERPJobStorage(self.session)
        storage.store(test_job)
        stored = self.queue_job.search([('uuid', '=', test_job.uuid)])
        stored.unlink()
        with self.assertRaises(NoSuchJobError):
            storage.load(test_job.uuid)

    def test_unicode(self):
        test_job = Job(func=dummy_task_args,
                       model_name='res.users',
                       args=(u'öô¿‽', u'ñě'),
                       kwargs={'c': u'ßø'},
                       priority=15,
                       description=u"My dé^Wdescription")
        test_job.user_id = 1
        storage = OpenERPJobStorage(self.session)
        storage.store(test_job)
        job_read = storage.load(test_job.uuid)
        self.assertEqual(test_job.args, job_read.args)
        self.assertEqual(job_read.args, ('res.users', u'öô¿‽', u'ñě'))
        self.assertEqual(test_job.kwargs, job_read.kwargs)
        self.assertEqual(job_read.kwargs, {'c': u'ßø'})
        self.assertEqual(test_job.description, job_read.description)
        self.assertEqual(job_read.description, u"My dé^Wdescription")

    def test_accented_bytestring(self):
        test_job = Job(func=dummy_task_args,
                       model_name='res.users',
                       args=('öô¿‽', 'ñě'),
                       kwargs={'c': 'ßø'},
                       priority=15,
                       description="My dé^Wdescription")
        test_job.user_id = 1
        storage = OpenERPJobStorage(self.session)
        storage.store(test_job)
        job_read = storage.load(test_job.uuid)
        self.assertEqual(test_job.args, job_read.args)
        self.assertEqual(job_read.args, ('res.users', 'öô¿‽', 'ñě'))
        self.assertEqual(test_job.kwargs, job_read.kwargs)
        self.assertEqual(job_read.kwargs, {'c': 'ßø'})
        # the job's description has been created as bytestring but is
        # decoded to utf8 by the ORM so make them comparable
        self.assertEqual(test_job.description,
                         job_read.description.encode('utf8'))
        self.assertEqual(job_read.description,
                         "My dé^Wdescription".decode('utf8'))

    def test_job_delay(self):
        self.cr.execute('delete from queue_job')
        job(task_a)
        job_uuid = task_a.delay(self.session, 'res.users')
        stored = self.queue_job.search([])
        self.assertEqual(len(stored), 1)
        self.assertEqual(
            stored.uuid,
            job_uuid,
            'Incorrect returned Job UUID')

    def test_job_delay_args(self):
        self.cr.execute('delete from queue_job')
        job(dummy_task_args)
        task_a.delay(self.session, 'res.users', 'o', 'k', c='!')
        stored = self.queue_job.search([])
        self.assertEqual(len(stored), 1)


class TestJobModel(common.TransactionCase):

    def setUp(self):
        super(TestJobModel, self).setUp()
        self.session = ConnectorSession(self.cr, self.uid)
        self.queue_job = self.env['queue.job']
        self.user = self.env['res.users']

    def _create_job(self):
        test_job = Job(func=task_a)
        storage = OpenERPJobStorage(self.session)
        storage.store(test_job)
        stored = storage.db_record_from_uuid(test_job.uuid)
        self.assertEqual(len(stored), 1)
        return stored

    def test_job_change_state(self):
        stored = self._create_job()
        stored._change_job_state(DONE, result='test')
        self.assertEqual(stored.state, DONE)
        self.assertEqual(stored.result, 'test')
        stored._change_job_state(PENDING, result='test2')
        self.assertEqual(stored.state, PENDING)
        self.assertEqual(stored.result, 'test2')
        with self.assertRaises(ValueError):
            # only PENDING and DONE supported
            stored._change_job_state(STARTED)

    def test_button_done(self):
        stored = self._create_job()
        stored.button_done()
        self.assertEqual(stored.state, DONE)
        self.assertEqual(stored.result,
                         'Manually set to done by %s' % self.env.user.name)

    def test_requeue(self):
        stored = self._create_job()
        stored.write({'state': 'failed'})
        stored.requeue()
        self.assertEqual(stored.state, PENDING)

    def test_message_when_write_fail(self):
        stored = self._create_job()
        stored.write({'state': 'failed'})
        self.assertEqual(stored.state, FAILED)
        messages = stored.message_ids
        self.assertEqual(len(messages), 2)

    def test_follower_when_write_fail(self):
        """Check that inactive users doesn't are not followers even if
        they are linked to an active partner"""
        group = self.env.ref('connector.group_connector_manager')
        vals = {'name': 'xx',
                'login': 'xx',
                'groups_id': [(6, 0, [group.id])],
                'active': False,
                }
        inactiveusr = self.user.create(vals)
        inactiveusr.partner_id.active = True
        self.assertFalse(inactiveusr in group.users)
        stored = self._create_job()
        stored.write({'state': 'failed'})
        followers = stored.message_follower_ids.mapped('partner_id')
        self.assertFalse(inactiveusr.partner_id in followers)
        self.assertFalse(
            set([u.partner_id for u in group.users]) - set(followers))

    def test_autovacuum(self):
        stored = self._create_job()
        stored2 = self._create_job()
        stored.write({'date_done': '2000-01-01 00:00:00'})
        stored2.write({'date_done': '2000-01-01 00:00:00', 'active': False})
        self.env['queue.job'].autovacuum()
        self.assertEqual(len(self.env['queue.job'].search([])), 0)

    def test_wizard_requeue(self):
        stored = self._create_job()
        stored.write({'state': 'failed'})
        model = self.env['queue.requeue.job']
        model = model.with_context(active_model='queue.job',
                                   active_ids=stored.ids)
        model.create({}).requeue()
        self.assertEqual(stored.state, PENDING)

    def test_context_uuid(self):
        test_job = Job(func=dummy_task_context)
        result = test_job.perform(self.session)
        key_present = 'job_uuid' in result
        self.assertTrue(key_present)
        self.assertEqual(result['job_uuid'], test_job._uuid)


class TestJobStorageMultiCompany(common.TransactionCase):
    """ Test storage of jobs """

    def setUp(self):
        super(TestJobStorageMultiCompany, self).setUp()
        self.session = ConnectorSession(self.cr, self.uid, context={})
        self.queue_job = self.env['queue.job']
        grp_connector_manager = self.ref("connector.group_connector_manager")
        User = self.env['res.users']
        Company = self.env['res.company']
        Partner = self.env['res.partner']
        self.other_partner_a = Partner.create(
            {"name": "My Company a",
             "is_company": True,
             "email": "test@tes.ttest",
             })
        self.other_company_a = Company.create(
            {"name": "My Company a",
             "partner_id": self.other_partner_a.id,
             "rml_header1": "My Company Tagline",
             "currency_id": self.ref("base.EUR")
             })
        self.other_user_a = User.create(
            {"partner_id": self.other_partner_a.id,
             "company_id": self.other_company_a.id,
             "company_ids": [(4, self.other_company_a.id)],
             "login": "my_login a",
             "name": "my user",
             "groups_id": [(4, grp_connector_manager)]
             })
        self.other_partner_b = Partner.create(
            {"name": "My Company b",
             "is_company": True,
             "email": "test@tes.ttest",
             })
        self.other_company_b = Company.create(
            {"name": "My Company b",
             "partner_id": self.other_partner_b.id,
             "rml_header1": "My Company Tagline",
             "currency_id": self.ref("base.EUR")
             })
        self.other_user_b = User.create(
            {"partner_id": self.other_partner_b.id,
             "company_id": self.other_company_b.id,
             "company_ids": [(4, self.other_company_b.id)],
             "login": "my_login_b",
             "name": "my user 1",
             "groups_id": [(4, grp_connector_manager)]
             })

    def _create_job(self):
        self.cr.execute('delete from queue_job')
        job(task_a)
        task_a.delay(self.session, 'res.users')
        stored = self.queue_job.search([])
        self.assertEqual(len(stored), 1)
        return stored

    def test_job_default_company_id(self):
        """the default company is the one from the current user_id"""
        stored = self._create_job()
        self.assertEqual(stored.company_id.id,
                         self.ref("base.main_company"),
                         'Incorrect default company_id')
        with self.session.change_user(self.other_user_b.id):
            stored = self._create_job()
            self.assertEqual(stored.company_id.id,
                             self.other_company_b.id,
                             'Incorrect default company_id')

    def test_job_no_company_id(self):
        """ if we put an empty company_id in the context
         jobs are created without company_id"""
        with self.session.change_context({'company_id': None}):
            stored = self._create_job()
            self.assertFalse(stored.company_id,
                             ' Company_id should be empty')

    def test_job_specific_company_id(self):
        """If a company_id specified in the context
        it's used by default for the job creation"""
        s = self.session
        with s.change_context({'company_id': self.other_company_a.id}):
            stored = self._create_job()
            self.assertEqual(stored.company_id.id,
                             self.other_company_a.id,
                             'Incorrect company_id')

    def test_job_subscription(self):
        # if the job is created without company_id, all members of
        # connector.group_connector_manager must be followers
        User = self.env['res.users']
        with self.session.change_context(company_id=None):
            stored = self._create_job()
        stored._subscribe_users()
        users = User.search(
            [('groups_id', '=', self.ref('connector.group_connector_manager'))]
        )
        self.assertEqual(len(stored.message_follower_ids), len(users))
        expected_partners = [u.partner_id for u in users]
        self.assertSetEqual(
            set(stored.message_follower_ids.mapped('partner_id')),
            set(expected_partners))
        followers_id = stored.message_follower_ids.mapped('partner_id.id')
        self.assertIn(self.other_partner_a.id, followers_id)
        self.assertIn(self.other_partner_b.id, followers_id)
        # jobs created for a specific company_id are followed only by
        # company's members
        s = self.session
        with s.change_context(company_id=self.other_company_a.id):
            stored = self._create_job()
        stored.sudo(self.other_user_a.id)._subscribe_users()
        # 2 because admin + self.other_partner_a
        self.assertEqual(len(stored.message_follower_ids), 2)
        users = User.browse([SUPERUSER_ID, self.other_user_a.id])
        expected_partners = [u.partner_id for u in users]
        self.assertSetEqual(
            set(stored.message_follower_ids.mapped('partner_id')),
            set(expected_partners))
        followers_id = stored.message_follower_ids.mapped('partner_id.id')
        self.assertIn(self.other_partner_a.id, followers_id)
        self.assertNotIn(self.other_partner_b.id, followers_id)


class TestJobChannels(common.TransactionCase):

    def setUp(self):
        super(TestJobChannels, self).setUp()
        self.function_model = self.env['queue.job.function']
        self.channel_model = self.env['queue.job.channel']
        self.job_model = self.env['queue.job']
        self.root_channel = self.env.ref('connector.channel_root')
        self.session = ConnectorSession(self.cr, self.uid, context={})

    def test_channel_complete_name(self):
        channel = self.channel_model.create({'name': 'number',
                                             'parent_id': self.root_channel.id,
                                             })
        subchannel = self.channel_model.create({'name': 'five',
                                                'parent_id': channel.id,
                                                })
        self.assertEquals(channel.complete_name, 'root.number')
        self.assertEquals(subchannel.complete_name, 'root.number.five')

    def test_channel_tree(self):
        with self.assertRaises(exceptions.ValidationError):
            self.channel_model.create({'name': 'sub'})

    def test_channel_root(self):
        with self.assertRaises(exceptions.Warning):
            self.root_channel.unlink()
        with self.assertRaises(exceptions.Warning):
            self.root_channel.name = 'leaf'

    def test_register_jobs(self):
        job(task_a)
        job(task_b)
        self.function_model._register_jobs()
        path_a = 'openerp.addons.connector.tests.test_job.task_a'
        path_b = 'openerp.addons.connector.tests.test_job.task_b'
        self.assertTrue(self.function_model.search([('name', '=', path_a)]))
        self.assertTrue(self.function_model.search([('name', '=', path_b)]))

    def test_channel_on_job(self):
        job(task_a)
        self.function_model._register_jobs()
        path_a = '%s.%s' % (task_a.__module__, task_a.__name__)
        job_func = self.function_model.search([('name', '=', path_a)])
        self.assertEquals(job_func.channel, 'root')

        test_job = Job(func=task_a)
        storage = OpenERPJobStorage(self.session)
        storage.store(test_job)
        stored = self.job_model.search([('uuid', '=', test_job.uuid)])
        self.assertEquals(stored.channel, 'root')

        channel = self.channel_model.create({'name': 'sub',
                                             'parent_id': self.root_channel.id,
                                             })
        job_func.channel_id = channel

        test_job = Job(func=task_a)
        storage = OpenERPJobStorage(self.session)
        storage.store(test_job)
        stored = self.job_model.search([('uuid', '=', test_job.uuid)])
        self.assertEquals(stored.channel, 'root.sub')

    def test_default_channel(self):
        self.function_model.search([]).unlink()
        job(task_a, default_channel='root.sub.subsub')
        self.assertEquals(task_a.default_channel, 'root.sub.subsub')

        self.function_model._register_jobs()

        path_a = '%s.%s' % (task_a.__module__, task_a.__name__)
        job_func = self.function_model.search([('name', '=', path_a)])

        self.assertEquals(job_func.channel, 'root.sub.subsub')
        channel = job_func.channel_id
        self.assertEquals(channel.name, 'subsub')
        self.assertEquals(channel.parent_id.name, 'sub')
        self.assertEquals(channel.parent_id.parent_id.name, 'root')

    def test_job_decorator(self):
        """ Test the job decorator """
        default_channel = 'channel'
        retry_pattern = {1: 5}
        partial = job(None, default_channel=default_channel,
                      retry_pattern=retry_pattern)
        self.assertEquals(partial.keywords.get('default_channel'),
                          default_channel)
        self.assertEquals(partial.keywords.get('retry_pattern'), retry_pattern)
