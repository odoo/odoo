# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.addons.digest.tests.common import TestDigestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWebsiteDigest(TestDigestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        cls.reference_now = fields.Datetime.from_string('2024-02-01 14:00:00')
        cls.periods = [
            (idx, cls.reference_now + timedelta(days=(-start)), cls.reference_now + timedelta(days=(-end)))
            for idx, (start, end) in enumerate(((10, 0), (20, 10), (30, 20), (40, 30)))
        ]
        for website, partner_id, track_days in (
                (cls.website_1, cls.partner_1.id, (5, 6, 7)),  # period 0 (3 tracks)
                (cls.website_1, cls.partner_2.id, (1, 4, 15, 16, 17)),  # period 0 (2 tracks), 1 (3 tracks)
                (cls.website_1, cls.partner_3.id, (17, 25)),  # period 1 (1 tracks), 2 (1 track)
                (cls.website_2, cls.partner_4.id, (27, 25)),  # period 2 (2 tracks)
                (cls.website_2, None, (8,)),  # period 0 (1 track)
        ):
            visitor = cls.env['website.visitor'].create({
                'website_id': website.id,
                'partner_id': partner_id,
                'last_connection_datetime': cls.reference_now + timedelta(days=(-1)),
                'access_token': partner_id or 'f9d2526d9c15658bdc91d2119e54b554',
            })
            page = page_per_website[website]
            for track_day in track_days:
                cls.env['website.track'].create({
                    'visitor_id': visitor.id,
                    'page_id': page.id,
                    'url': page.url,
                    'visit_datetime': cls.reference_now + timedelta(days=(-track_day)),
                })

    def test_kpi_website_visitors_count_value(self):
        for digest, expected_counts in ((self.digest_1, (2, 2, 1, 0)),
                                        (self.digest_2, (1, 0, 1, 0)),
                                        (self.digest_3, (2, 2, 1, 0))):
            for (period_idx, start, end), expected_count in zip(self.periods, expected_counts):
                self.env['digest.digest'].invalidate_model(['kpi_website_visitor_count_value'])
                self.assertEqual(
                    digest.with_context(start_datetime=start, end_datetime=end).kpi_website_visitor_count_value,
                    expected_count,
                    f'{digest.name}, period {period_idx}')

    def test_kpi_website_track_count_value(self):
        for digest, expected_counts in ((self.digest_1, (5, 4, 1, 0)),
                                        (self.digest_2, (1, 0, 2, 0)),
                                        (self.digest_3, (5, 4, 1, 0))):
            for (period_idx, start, end), expected_count in zip(self.periods, expected_counts):
                self.env['digest.digest'].invalidate_model(['kpi_website_track_count_value'])
                self.assertEqual(
                    digest.with_context(start_datetime=start, end_datetime=end).kpi_website_track_count_value,
                    expected_count,
                    f'{digest.name}, period {period_idx}')
