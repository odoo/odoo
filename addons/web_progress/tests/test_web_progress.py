from odoo.tests import common, tagged
from odoo import exceptions, api, registry
from odoo.tools import mute_logger
from psycopg2 import ProgrammingError
import uuid
import logging
from ..models.web_progress import last_report_time

_logger = logging.getLogger(__name__)


@tagged('at_install', '-post_install')
class WebProgressTest(common.TransactionCase):

    def check_all_progress_data_empty(self):
        """
        Check that all global progress data is empty after tests
        """
        self.assertFalse(last_report_time, msg="Global variable last_report_time shall be empty by now")

    def setUp(self):
        super(WebProgressTest, self).setUp()
        self.maxDiff = None
        self.partner_obj = self.env['res.partner']
        self.web_progress_obj = self.env['web.progress']
        self.partner_ids = self.partner_obj
        self.partner_vals = {}
        for idx in range(20):
            self.partner_vals[idx] = dict(name='Test{}'.format(idx),
                                          email='email{}@test.me'.format(idx))
            self.partner_ids |= self.partner_obj.create(dict(self.partner_vals[idx]))
        self.addCleanup(self.check_all_progress_data_empty)

    def _check_web_progress_iter_recordset(self, total, recur_level=0):
        """
        Check that web_progress_iter works correctly for a recordset
        :param total: total number of collection elements
        """
        progress_iter = self.partner_ids[:total].with_progress(msg="Total {} Level {}".format(total,
                                                                                              recur_level))
        self.assertEqual(len(progress_iter), total, msg="Length shall be accessible")
        if total > 0:
            self.assertEqual(progress_iter[0], self.partner_ids[0], msg="Indexing shall be accessible")
            self.assertEqual(progress_iter._name, self.partner_ids._name, msg="Attributes shall be accessible")
        if total == len(self.partner_ids):
            self.assertEqual(progress_iter.ids, self.partner_ids.ids, msg="Attributes shall be accessible")
        count = 0
        for idx, partner_id in zip(range(total),progress_iter):
            self.assertEqual(partner_id.name, self.partner_vals[idx]['name'].format(idx), msg="Wrong name")
            self.assertEqual(partner_id.email, self.partner_vals[idx]['email'].format(idx), msg="Wrong email")
            count += 1
            if recur_level > 0:
                self._check_web_progress_iter_recordset(total, recur_level - 1)
        self.assertEqual(count, total, msg="Not all elements are yielded from a collection")

    def _check_web_progress_iter_recordset_many(self, recur_level=0):
        """
        Iterate recordsets of different lengths
        :param recur_level: recursion level of iterations
        """
        # iterate all partners
        self._check_web_progress_iter_recordset(len(self.partner_ids), recur_level)
        # iterate half of all partners
        self._check_web_progress_iter_recordset(round(len(self.partner_ids)/2), recur_level)
        # iterate again all partners (no recursion)
        self._check_web_progress_iter_recordset(len(self.partner_ids))
        # iterate one partner
        self._check_web_progress_iter_recordset(1, recur_level)
        # iterate empty recordset
        self._check_web_progress_iter_recordset(0, recur_level)

    def _check_web_progress_cancelled(self):
        """
        Checks that the current operation has been cancelled
        """
        code = self.partner_ids._context.get('progress_code', None)
        self.assertIsNotNone(code, msg="Progress code shall be in the context")
        cancelled = self.web_progress_obj._check_cancelled(dict(code=code))
        self.assertTrue(cancelled, msg="Currect operation should have been cancelled")

    def test_web_progress_iter_without_web_progress_code(self):
        """
        Check that web_progress_iter works correctly without a progress_code in context
        """
        self._check_web_progress_iter_recordset_many(0)
        self._check_web_progress_iter_recordset_many(1)

    def test_web_progress_iter_with_web_progress_code(self):
        """
        Check that web_progress_iter works correctly with a progress_code in context
        """
        progress_code = str(uuid.uuid4())
        self.partner_ids = self.partner_ids.with_context(progress_code=progress_code)
        self._check_web_progress_iter_recordset_many(0)
        self._check_web_progress_iter_recordset_many(1)

    def test_web_progress_iter_with_web_progress_code_cancel(self):
        """
        Check that cancel request is respected by web_progress_iter
        """
        progress_code = str(uuid.uuid4())
        self.partner_ids = self.partner_ids.with_context(progress_code=progress_code)
        self._check_web_progress_iter_recordset_many(0)
        self.partner_ids.web_progress_cancel()
        self._check_web_progress_cancelled()
        # any further iteration shall raise UserError
        with self.assertRaises(exceptions.UserError, msg="Exception UserErro shall have been raised"):
            self._check_web_progress_iter_recordset_many(0)
        self._check_web_progress_cancelled()

    def test_web_progress_percent(self):
        """
        Check web_progress_percent
        """
        progress_code = str(uuid.uuid4())
        self.partner_ids = self.partner_ids.with_context(progress_code=progress_code)
        self.partner_ids.web_progress_percent(0, "Start")
        self.partner_ids.web_progress_percent(50, "Middle")
        self.partner_ids.web_progress_percent(100, "End")


class WebProgressTestAllProgress(common.TransactionCase):
    at_install = True
    post_install = False

    @mute_logger('odoo.sql_db')
    def test_get_all_progress(self):
        """
        Check call to get_all_progress without and with parameters.
        Verify if the parameter is properly escaped in the internal SQL query.
        """
        progress_code = str(uuid.uuid4())
        partner_obj = self.env['res.partner'].with_context(progress_code=progress_code)
        partner_obj.web_progress_percent(0, "Start")
        with registry(self.env.cr.dbname).cursor() as new_cr:
            # Create a new environment with a new cursor
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            progress_obj = self.env['web.progress'].with_env(new_env)
            res = progress_obj.get_all_progress()
            self.assertEqual(res, [{'code': progress_code}])
            res = progress_obj.get_all_progress(0)
            self.assertEqual(res, [])
            with self.assertRaises(ProgrammingError) as e:
                progress_obj.get_all_progress("0 SECOND' GROUP BY code; "
                                              "SELECT code, array_agg(state) FROM web_progress "
                                              "WHERE create_date > timezone('utc', now()) - INTERVAL '10")
            new_cr.rollback()
