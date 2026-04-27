# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestQualityAlert(TransactionCase):

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()

        cls.stage_0 = cls.env['quality.alert.stage'].create({'name': 'Quality Stage 0'})
        cls.stage_1 = cls.env['quality.alert.stage'].create({'name': 'Quality Stage 1'})
        cls.done_stage = cls.env['quality.alert.stage'].create({'name': 'Done Stage', 'done': True})

        cls.alert_0 = cls.env['quality.alert'].create({
            'name': 'Quality Alert 0', 'stage_id': cls.stage_0.id,
        })
        cls.alert_1 = cls.env['quality.alert'].create({
            'name': 'Quality Alert 1', 'stage_id': cls.stage_1.id,
        })

        return res

    def test_write(self):
        alerts = self.alert_0 | self.alert_1
        # Writing on a records set with different stages should not raise an error
        alerts.write({'description': 'Quality Alerts'})
        # Setting the a done stage should set a closed date
        alerts.write({'stage_id': self.done_stage.id})
        self.assertTrue(all(alerts.mapped('date_close')), 'date_close should have been set')
        self.assertEqual(
            *alerts.mapped('date_close'), 'date_close should have been the same for both alerts')
