# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


@common.bundles('hr.common')
class TestHrCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestHrCommon, cls).setUpClass()

        cls.res_users_hr_officer = cls.quick_ref('hr.user_hr_officer')

    @classmethod
    def quick_ref(cls, xmlid):
        """Find the matching record, without an existence check."""
        model, id = cls.env['ir.model.data']._xmlid_to_res_model_res_id(xmlid)
        return cls.env[model].browse(id)
