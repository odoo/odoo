# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
import functools
import logging

from odoo import sql_db
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)
sql_logger = logging.getLogger('odoo.sql_db')


def queryCount(**counters):
    """ Decorate a method to check the number of queries it makes. """
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self):
            users = self.env['res.users']
            for user_name in counters.keys():
                users = users + getattr(self, user_name, self.env['res.users'])
            for user in users:
                # switch user
                self.uid = user.id
                self.env = self.env(user=self.uid)
                # warm up the caches
                self._round = False
                func(self)
                self.env.cache.invalidate()
                # test for real, and check query count
                self._round = True
                self.resetQueryCount()
                if self.debugMode():
                    with sql_db._enable_full_sql_log:
                        func(self)
                else:
                    func(self)
                self.assertQueryCount(self.cr.sql_log_count - self._count,
                                      counters[user.login], user.login)

        return wrapper

    return decorate


class TestPerformance(TransactionCase):

    def setUp(self):
        super(TestPerformance, self).setUp()
        self._debug = False

    def assertQueryCount(self, actual, expected, message):
        self.assertLessEqual(actual, expected, message)
        if actual < expected:
            _logger.info("Warning: Got %d queries instead of %d: %s", actual, expected, message)

    def debugMode(self):
        return self._debug

    def resetQueryCount(self):
        """ Reset the query counter. """
        self._count = self.cr.sql_log_count

    def str(self, value):
        """ Return a value different from run to run. """
        return value + 'z' if self._round else value

    def int(self, value):
        """ Return a value different from run to run. """
        return value + 1 if self._round else value

    @contextmanager
    def queryCheck(self, expected, message):
        pass
        # # warm up the caches
        # self._round = False
        # func(self)
        # self.env.cache.invalidate()
        # # test for real, and check query count
        # self._round = True
        # self.resetQueryCount()
        # if self.debugMode():
        #     with sql_db._enable_full_sql_log:
        #         func(self)
        # else:
        #     func(self)
        # self.assertQueryCount(self.cr.sql_log_count - self._count,
        #                       counters[user.login], user.login)
