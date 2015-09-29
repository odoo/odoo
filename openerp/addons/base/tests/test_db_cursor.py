# -*- coding: utf-8 -*-

import unittest

import openerp
from openerp.tools.misc import mute_logger
from openerp.tests import common

ADMIN_USER_ID = common.ADMIN_USER_ID

def registry():
    return openerp.modules.registry.RegistryManager.get(common.get_db_name())


class test_cr_execute(unittest.TestCase):
    """ Try cr.execute with wrong parameters """

    @mute_logger('openerp.sql_db')
    def test_execute_bad_params(self):
        """
        Try to use iterable but non-list or int params in query parameters.
        """
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE login=%s", 'admin')
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE id=%s", 1)
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE id=%s", '1')
