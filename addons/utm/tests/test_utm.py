# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.utm.models.utm_mixin import UtmMixin
from odoo.addons.utm.tests.common import TestUTMCommon
from odoo.tests import tagged


@tagged("utm", "post_install", "-at_install")
class TestUtm(TestUTMCommon):

    def test_campaign_automatic_name(self):
        """ Test automatic naming of campaigns based on title """
        campaigns = self.env["utm.campaign"].create([
            {"title": "Title"},
            {"name": "ForcedName", "title": "WithTitle"}
        ])
        self.assertEqual(campaigns[0].name, "Title")
        self.assertEqual(campaigns[1].name, "ForcedName")

        campaigns[0].title = "ForcedName"
        self.assertEqual(campaigns[0].name, "ForcedName [2]")
        self.assertEqual(campaigns[0].name, "ForcedName [2]")

    def test_find_or_create_record(self):
        """ Tests for '_find_or_create_record' """
        source_1, source_2 = self.env['utm.source'].create([{
            'name': 'Source 1',
        }, {
            'name': 'Source 2',
        }])

        # Find the record based on the given name
        source = self.env['utm.mixin']._find_or_create_record('utm.source', 'Source 1')
        self.assertEqual(source, source_1)
        source = self.env['utm.mixin']._find_or_create_record('utm.source', 'Source 2')
        self.assertEqual(source, source_2)

        # Create a new record
        source_3 = self.env['utm.mixin']._find_or_create_record('utm.source', 'Source 3')
        self.assertNotIn(source_3, source_1 | source_2)
        self.assertEqual(source_3.name, 'Source 3')

        # Duplicate mark: valid new record
        source_3_2 = self.env['utm.mixin']._find_or_create_record('utm.source', 'Source 3 [2]')
        self.assertNotIn(source_3_2, source_1 | source_2 | source_3)
        self.assertEqual(source_3_2.name, 'Source 3 [2]')

        # New source with duplicate mark ...
        source_4_2 = self.env['utm.mixin']._find_or_create_record('utm.source', 'Source 4 [2]')
        self.assertNotIn(source_4_2, source_1 | source_2 | source_3 | source_3_2)
        self.assertEqual(source_4_2.name, 'Source 4 [2]')
        source_4_2_bis = self.env['utm.mixin']._find_or_create_record('utm.source', 'Source 4 [2]')
        self.assertEqual(source_4_2_bis, source_4_2)
        # ... then basic without duplicate mark
        source_4 = self.env['utm.mixin']._find_or_create_record('utm.source', 'Source 4')
        self.assertNotIn(source_4, source_1 | source_2 | source_3 | source_3_2 | source_4_2)
        self.assertEqual(source_4.name, 'Source 4')

    def test_find_or_create_record_case(self):
        """ Find-or-create should be case insensitive to avoid useless duplication """
        name = "LinkedIn Plus"
        source = self.env["utm.mixin"]._find_or_create_record("utm.source", name)
        self.assertEqual(source.name, name)

        # case insensitive equal (also strip spaces)
        for src in ("linkedin plus", "Linkedin plus", "LINKEDIN PLUS", f"{name} ", f" {name}"):
            with self.subTest(src=src):
                found = self.env['utm.mixin']._find_or_create_record("utm.source", src)
                self.assertEqual(found, source)
        # not equal, just to be sure we don't do a pure ilike
        for src in ("LinkedIn", "Plus"):
            with self.subTest(src=src):
                found = self.env['utm.mixin']._find_or_create_record("utm.source", src)
                self.assertNotEqual(found, source)

    def test_find_or_create_with_archived_record(self):
        archived_campaign = self.env['utm.campaign'].create([{
            'active': False,
            'name': 'Archived Campaign',
        }])
        campaign = self.env['utm.mixin']._find_or_create_record('utm.campaign', 'Archived Campaign')
        self.assertEqual(archived_campaign, campaign, "An archived record must be found instead of re-created.")

    def test_name_generation(self):
        """Test that the name is always unique. A counter must be added at the
        end of the name if it's not the case."""
        for utm_model in ('utm.source', 'utm.medium', 'utm.campaign'):
            utm_0 = self.env[utm_model].create({'name': 'UTM new'})

            utm_1, utm_2, utm_3, utm_4, utm_5 = self.env[utm_model].create([
                {
                    'name': 'UTM 1',
                }, {
                    'name': 'UTM 2',
                }, {
                    # UTM record 3 has the same name of the previous UTM record
                    'name': 'UTM new',
                }, {
                    # UTM record 4 has the same name of the previous UTM record
                    'name': 'UTM new',
                }, {
                    # UTM record 5 has the same name of the previous UTM record
                    # but with a wrong counter part, it should be removed and updated
                    'name': 'UTM new [0]',
                },
            ])

            self.assertEqual(utm_0.name, 'UTM new', msg='The first "UTM dup" should be left unchanged since it is unique')
            self.assertEqual(utm_1.name, 'UTM 1', msg='This name is already unique')
            self.assertEqual(utm_2.name, 'UTM 2', msg='This name is already unique')
            self.assertEqual(utm_3.name, 'UTM new [2]', msg='Must add a counter as suffix to ensure uniqueness')
            self.assertEqual(utm_4.name, 'UTM new [3]', msg='Must add a counter as suffix to ensure uniqueness')
            self.assertEqual(utm_5.name, 'UTM new [4]', msg='Must add a counter as suffix to ensure uniqueness')

            (utm_0 | utm_3 | utm_4).unlink()

            utm_new_multi = self.env[utm_model].create([{'name': 'UTM new'} for _ in range(4)])
            self.assertListEqual(
                utm_new_multi.mapped('name'),
                ['UTM new', 'UTM new [2]', 'UTM new [3]', 'UTM new [5]'],
                'Duplicate counters should be filled in order of missing.')

            # no ilike-based duplicate
            utm_7 = self.env[utm_model].create({'name': 'UTM ne'})
            self.assertEqual(
                utm_7.name, 'UTM ne',
                msg='Even if this name has the same prefix as the other, it is still unique')

            # copy should avoid uniqueness issues
            utm_8 = utm_7.copy()
            self.assertEqual(
                utm_8.name, 'UTM ne [2]',
                msg='Must add a counter as suffix to ensure uniqueness')

        # Test name uniqueness when creating a campaign using a title (quick creation)
        utm_9 = self.env['utm.campaign'].create({'title': 'UTM ne'})
        self.assertEqual(
            utm_9.name, 'UTM ne [3]',
            msg='Even if the record has been created using a title, the name must be unique')

    def test_name_generation_duplicate_marks(self):
        """ Check corner cases when giving duplicate marks directly in name """
        for utm_model in ('utm.source', 'utm.medium', 'utm.campaign'):
            utm = self.env[utm_model].create({"name": "MarkTest [2]"})
            self.assertEqual(
                utm.name, "MarkTest [2]",
                "Should respect creation value")

            utm.write({"name": "MarkTest [2]"})
            self.assertEqual(
                utm.name, "MarkTest [2]",
                "Writing same value: should not auto increment")

            utm.write({"name": "MarkTest"})
            self.assertEqual(
                utm.name, "MarkTest",
                "First available counter")

            utm.write({"name": "MarkTest [8]"})
            self.assertEqual(
                utm.name, "MarkTest [8]",
                "Should respect given values")

            utm_batch = self.env[utm_model].create([
                {"name": "BatchTest [2]"}
                for x in range(4)
            ])
            self.assertEqual(
                utm_batch.mapped("name"),
                ["BatchTest [2]", "BatchTest", "BatchTest [3]", "BatchTest [4]"],
                "Accept input if possible, otherwise increment"
            )

            utm_batch_nodup = self.env[utm_model].create([
                {"name": "NoDupBatch [2]"},
                {"name": "NoDupBatch [4]"},
                {"name": "NoDupBatch [6]"},
                {"name": "Margoulin"},
            ])
            self.assertEqual(
                utm_batch_nodup.mapped("name"),
                ["NoDupBatch [2]", "NoDupBatch [4]", "NoDupBatch [6]", "Margoulin"]
            )

    def test_split_name_and_count(self):
        """ Test for tool '_split_name_and_count' """
        for name, (expected_name, expected_count) in [
            ("medium", ("medium", 1)),
            ("medium [0]", ("medium", 0)),
            ("medium [1]", ("medium", 1)),
            ("medium [x]", ("medium [x]", 1)),  # not integer -> do not care
            ("medium [0", ("medium [0", 1)),  # unrecognized -> do not crash
        ]:
            with self.subTest(name=name):
                self.assertEqual(UtmMixin._split_name_and_count(name), (expected_name, expected_count))
