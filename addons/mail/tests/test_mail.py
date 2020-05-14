# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPerformance(TransactionCase):
    def test_mail_create_batch(self):
        """Enforce main mail models create overrides support batch record creation."""
        self.assertModelCreateMulti("mail.mail")
        self.assertModelCreateMulti("mail.message")
        self.assertModelCreateMulti("mail.notification")
        self.assertModelCreateMulti("mail.thread")
        self.assertModelCreateMulti("mail.followers")
        self.assertModelCreateMulti("mail.alias.mixin", [dict(alias_id=i+1) for i in range(2)])
