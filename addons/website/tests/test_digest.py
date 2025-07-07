# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from freezegun import freeze_time

from odoo import fields
from odoo.addons.digest.tests.common import TestDigestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWebsiteDigest(TestDigestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['website.track'].search([]).unlink()
        cls.reference_now = fields.Datetime.from_string('2024-02-05 11:11:34')
        cls.kpi_website_visitor_count = cls.env.ref('website.kpi_website_visitor_count')
        cls.kpi_website_track_count = cls.env.ref('website.kpi_website_track_count')
        cls.all_digests.kpi_ids = cls.kpi_website_visitor_count | cls.kpi_website_track_count
        with freeze_time(cls.reference_now):
            cls.partner_1, cls.partner_2, cls.partner_3, cls.partner_4 = cls.env['res.partner'].create(
                [{'name': f'Test Partner {idx + 1}'} for idx in range(4)])
            cls.website_1, cls.website_2 = cls.env['website'].create([
                {'name': "Website 1", 'company_id': cls.company_1.id},
                {'name': "Website 2", 'company_id': cls.company_2.id},
            ])
            page_per_website = dict()
            for website_idx, website in enumerate((cls.website_1, cls.website_2)):
                page_per_website[website] = cls.env['website.page'].create({
                    'arch': f'<div>Home page of website {website_idx}</div>',
                    'is_published': True,
                    'key': 'test.homepage_url_test',
                    'name': 'HomepageUrlTest',
                    'type': 'qweb',
                    'url': f'/website_{website_idx}/homepage_url_test',
                    'website_id': website.id,
                })
            cls.now = fields.Datetime.now()
            for website, partner_id, track_hours_lst in (
                    (cls.website_1, cls.partner_1.id, (5 * 24, 6 * 24, 9 * 24)),  # 24h: 0, 7 days: 2, 30 days: 3
                    (cls.website_1, cls.partner_2.id, (1, 4, 15 * 24, 16 * 24, 17 * 24)),  # 24h: 2, 7d: 2, 30d: 5
                    (cls.website_1, cls.partner_3.id, (17 * 24, 25 * 24)),  # 30d: 2
                    (cls.website_2, cls.partner_4.id, (27 * 24, 25 * 24)),  # 30d: 2
                    (cls.website_2, None, (8,)),  # 24: 1, 7d: 1, 30d: 1
            ):
                visitor = cls.env['website.visitor'].create({
                    'website_id': website.id,
                    'partner_id': partner_id,
                    'last_connection_datetime': cls.now + timedelta(days=(-1)),
                    'access_token': partner_id or 'f9d2526d9c15658bdc91d2119e54b554',
                })
                page = page_per_website[website]
                for track_hours in track_hours_lst:
                    cls.env['website.track'].create({
                        'visitor_id': visitor.id,
                        'page_id': page.id,
                        'url': page.url,
                        'visit_datetime': cls.now + timedelta(hours=(-track_hours)),
                    })

    def test_kpi_website_visitors_count_value(self):
        for digest, period, expected_value in (
                (self.digest_1, 'value_last_30_days', 3),
                (self.digest_1, 'value_last_7_days', 2),
                (self.digest_1, 'value_last_24_hours', 1),
                (self.digest_2, 'value_last_30_days', 2),
                (self.digest_2, 'value_last_7_days', 1),
                (self.digest_2, 'value_last_24_hours', 1),
                (self.digest_3, 'value_last_30_days', 3),
                (self.digest_3, 'value_last_7_days', 2),
                (self.digest_3, 'value_last_24_hours', 1),
        ):
            with self.subTest(digest=digest.name, period=period), freeze_time(self.reference_now):
                self.assertEqual(
                    self._get_values(digest, self.kpi_website_visitor_count.name, period),
                    str(expected_value))

    def test_kpi_website_track_count_value(self):
        for digest, period, expected_value in (
                (self.digest_1, 'value_last_30_days', 10),
                (self.digest_1, 'value_last_7_days', 4),
                (self.digest_1, 'value_last_24_hours', 2),
                (self.digest_2, 'value_last_30_days', 3),
                (self.digest_2, 'value_last_7_days', 1),
                (self.digest_2, 'value_last_24_hours', 1),
                (self.digest_3, 'value_last_30_days', 10),
                (self.digest_3, 'value_last_7_days', 4),
                (self.digest_3, 'value_last_24_hours', 2),
        ):
            with self.subTest(digest=digest.name, period=period), freeze_time(self.reference_now):
                self.assertEqual(
                    self._get_values(digest, self.kpi_website_track_count.name, period),
                    str(expected_value))
