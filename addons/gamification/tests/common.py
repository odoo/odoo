# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, TransactionCaseWithUserDemo
from odoo.tests import TransactionCase


class HttpCaseGamification(HttpCaseWithUserDemo):

    def setUp(self):
        super().setUp()
        if not self.user_demo.karma:
            self.user_demo.karma = 2500


class TransactionCaseGamification(TransactionCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.user_demo.karma:
            cls.user_demo.karma = 2500


class TransactionCaseKarmaTracking(TransactionCase):

    @classmethod
    def _create_trackings(cls, user, karma, steps, track_date, days_delta=1):
        old_value = user.karma
        for _step in range(steps):
            new_value = old_value + karma
            cls.env['gamification.karma.tracking'].create([{
                'user_id': user.id,
                'old_value': old_value,
                'new_value': new_value,
                'consolidated': False,
                'tracking_date': fields.Datetime.to_string(track_date)
            }])
            old_value = new_value
            track_date = track_date + relativedelta(days=days_delta)
