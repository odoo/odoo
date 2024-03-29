# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.utm.tests.common import TestUTMCommon


class TestUtm(TestUTMCommon):
    def test_find_or_create_record(self):
        source_1, source_2 = self.env['utm.source'].create([{
            'name': 'Source 1',
        }, {
            'name': 'Source 2',
        }])

        # Find the record based on the given name
        source = self.env['utm.mixin']._find_or_create_record('utm.source', 'Source 1')
        self.assertEqual(source, source_1)

        # Create a new record
        source_4 = self.env['utm.mixin']._find_or_create_record('utm.source', 'Source 3')
        self.assertNotIn(source_4, source_1 | source_2)
        self.assertEqual(source_4.name, 'Source 3')

    def test_find_or_create_with_archived_record(self):
        archived_campaign = self.env['utm.campaign'].create([{
            'active': False,
            'name': 'Archived Campaign',
        }])
        campaign = self.env['utm.mixin']._find_or_create_record('utm.campaign', 'Archived Campaign')
        self.assertEqual(archived_campaign, campaign, "An archived record must be found instead of re-created.")

    def test_name_generation(self):
        """Test that the name is always unique.

        A counter must be added at the end of the name if it's not the case.
        """
        for utm_model in ('utm.source', 'utm.medium', 'utm.campaign'):
            utm_0 = self.env[utm_model].create({'name': 'UTM dup'})

            utm_1, utm_2, utm_3, utm_4, utm_5 = self.env[utm_model].create([{
                'name': 'UTM 1',
            }, {
                'name': 'UTM 2',
            }, {
                'name': 'UTM dup',
            }, {
                # UTM record 4 has the same name of the previous UTM record
                'name': 'UTM dup',
            }, {
                # UTM record 5 has the same name of the previous UTM record
                # but with a wrong counter part, it will be removed and updated
                'name': 'UTM dup [0]',
            }])

            self.assertEqual(utm_0.name, 'UTM dup', msg='The first "UTM dup" should be left unchanged since it is unique')
            self.assertEqual(utm_1.name, 'UTM 1', msg='This name is already unique')
            self.assertEqual(utm_2.name, 'UTM 2', msg='This name is already unique')
            self.assertEqual(utm_3.name, 'UTM dup [2]', msg='Must add a counter as suffix to ensure uniqueness')
            self.assertEqual(utm_4.name, 'UTM dup [3]', msg='Must add a counter as suffix to ensure uniqueness')
            self.assertEqual(utm_5.name, 'UTM dup [4]', msg='Must add a counter as suffix to ensure uniqueness')

            (utm_0 | utm_3 | utm_4).unlink()

            utm_6 = self.env[utm_model].create({'name': 'UTM dup'})
            self.assertEqual(utm_6.name, 'UTM dup [5]')

            utm_7 = self.env[utm_model].create({'name': 'UTM d'})
            self.assertEqual(utm_7.name, 'UTM d', msg='Even if this name has the same prefix as the other, it is still unique')

            utm_8 = utm_7.copy()
            self.assertEqual(utm_8.name, 'UTM d [2]', msg='Must add a counter as suffix to ensure uniqueness')

        # Test name uniqueness when creating a campaign using a title (quick creation)
        utm_9 = self.env['utm.campaign'].create({'title': 'UTM dup'})
        self.assertEqual(utm_9.name, 'UTM dup [6]', msg='Even if the record has been created using a title, the name must be unique')
