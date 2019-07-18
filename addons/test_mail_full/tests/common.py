# -*- coding: utf-8 -*-

from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.test_mail.tests import common as test_mail_common


class BaseFunctionalTest(test_mail_common.BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(BaseFunctionalTest, cls).setUpClass()
        cls.user_employee.write({'login': 'employee'})

        # update country to belgium in order to test sanitization of numbers
        cls.user_employee.company_id.write({'country_id': cls.env.ref('base.be').id})

        # some numbers for testing
        cls.random_numbers_str = '+32456998877, 0456665544'
        cls.random_numbers = cls.random_numbers_str.split(', ')
        cls.random_numbers_san = [phone_validation.phone_format(number, 'BE', '32', force_format='E164') for number in cls.random_numbers]
        cls.test_numbers = ['+32456010203', '0456 04 05 06', '0032456070809']
        cls.test_numbers_san = [phone_validation.phone_format(number, 'BE', '32', force_format='E164') for number in cls.test_numbers]

        # some numbers for mass testing
        cls.mass_numbers = ['04561%s2%s3%s' % (x, x, x) for x in range(0, 10)]
        cls.mass_numbers_san = [phone_validation.phone_format(number, 'BE', '32', force_format='E164') for number in cls.mass_numbers]
