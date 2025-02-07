# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.digest.tests.common import TestDigestCommon
from odoo.tools import mute_logger


class TestCrmDigest(TestDigestCommon):
    @classmethod
    @mute_logger('odoo.models.unlink')
    def setUpClass(cls):
        super().setUpClass()

        cls.env['crm.lead'].search([]).unlink()

        cls.env['crm.lead'].create([{
            'name': 'Lead 1',
            'company_id': cls.company_1.id,
            'probability': 100,
            'type': 'opportunity',
            'date_closed': datetime.now() - timedelta(days=1),
        }, {
            'name': 'Lead 2',
            'company_id': cls.company_1.id,
            'probability': 90,
            'type': 'opportunity',
            'date_closed': datetime.now() - timedelta(days=1),
        }, {
            'name': 'Lead 3',
            'company_id': False,
            'probability': 100,
            'type': 'opportunity',
            'date_closed': datetime.now() - timedelta(days=1),
        }, {
            'name': 'Lead 4',
            'company_id': cls.company_1.id,
            'probability': 100,
            'type': 'opportunity',
            'date_closed': datetime.now() - timedelta(days=700),
        }])
        cls.kpi_crm_opportunities_won = cls.env.ref('crm.kpi_crm_opportunities_won')
        for digest in cls.all_digests:
            digest.kpi_ids = cls.kpi_crm_opportunities_won

    def test_kpi_crm_lead_opportunities_won_value(self):
        kpi_name = self.kpi_crm_opportunities_won.name
        self.assertEqual(self._get_values(self.digest_1, kpi_name, 'value_last_30_days'), '2')
        self.assertEqual(self._get_values(self.digest_2, kpi_name, 'value_last_30_days'), '1',
            msg='This digest is in a different company')
        self.assertEqual(self._get_values(self.digest_3, kpi_name, 'value_last_30_days'), '2',
            msg='This digest has no company, should take the current one')

        self.digest_3.invalidate_recordset()
        self.assertEqual(
            self._get_values(self.digest_3.with_company(self.company_2), kpi_name, 'value_last_30_days'),
            '1',
        )
