# -*- coding: utf-8 -*-

from odoo.addons.test_mail.tests import common as test_mail_common


class BaseFunctionalTest(test_mail_common.BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(BaseFunctionalTest, cls).setUpClass()
        cls.user_employee.write({'login': 'employee'})

        # update country to belgium in order to test sanitization of numbers
        cls.user_employee.company_id.write({'country_id': cls.env.ref('base.be').id})
