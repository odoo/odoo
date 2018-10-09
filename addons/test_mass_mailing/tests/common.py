# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail.tests import common
from odoo.tests import tagged


@tagged('mass_mail')
class MassMailingCase(common.MockEmails, common.BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(MassMailingCase, cls).setUpClass()

        # be sure for some common data
        cls.user_employee.write({
            'login': 'emp',
        })

        cls.user_marketing = cls.env['res.users'].with_context(cls._quick_create_user_ctx).create({
            'name': 'Ernest Employee',
            'login': 'marketing',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notification_type': 'email',
            'groups_id': [
                (6, 0, [cls.env.ref('base.group_user').id]),
                (6, 0, [cls.env.ref('mass_mailing.group_mass_mailing_user').id])
            ],
        })
