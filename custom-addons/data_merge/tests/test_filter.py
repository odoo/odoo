# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import test_common
from odoo.tests.common import users

class TestFilter(test_common.TestCommon):

    @users('admin')
    def test_company_filter(self):
        """
            The purpose is to test the method `_search_company_id` which performs
            custom logic for searching on the `company_id` field.
        """
        PartnerModel = self.env['ir.model'].search([('model', '=', 'res.partner')])

        company = self.env['res.company'].create({'name': 'Company test'})
        self._create_record('res.partner', name='toto test', company_id=company.id)
        self._create_record('res.partner', name='toto test', company_id=company.id)

        MyModel = self.DMModel.create({
            'name': 'test of test partner',
            'res_model_id': PartnerModel.id,
            'domain': [('name', 'like', 'toto test')],
        })
        self.DMRule.create({
            'model_id': MyModel.id,
            'field_id': self.env['ir.model.fields']._get('res.partner', 'name').id,
            'match_mode': 'exact'
        })

        MyModel.find_duplicates()
        self.env['data_merge.record'].flush_model()

        records = self.DMRecord.with_context(data_merge_model_ids=tuple(MyModel.ids)).search([('company_id', 'ilike', 'test')])
        self.assertEqual(len(records), 2)
