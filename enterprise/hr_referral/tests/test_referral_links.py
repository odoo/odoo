# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_join
from odoo.tests import tagged, HttpCase

from .common import TestHrReferralBase


@tagged('post_install', '-at_install')
class TestReferralLinks(TestHrReferralBase, HttpCase):

    def test_search_or_create_referral_links(self):
        '''
        Test the search_or_create_referral_links method of the hr.job model

        This method will test the uniqueness of each link between users and
        between channel. Finally, it will test if no new link have
        been created after the second call of the method.
        '''

        users = self.env['res.users'].search([])
        job = self.env['hr.job'].create({
            'name': 'test_search_or_create_referral_links',
            'no_of_recruitment': '5',
            'is_published': True,
            'department_id': self.dep_rd.id,
            'company_id': self.company_1.id,
        })

        links_by_user_by_channel = {}
        links = []
        for channel in ['direct', 'facebook', 'twitter', 'linkedin']:
            # check the uniqueness of the links between users
            channel_links = job.search_or_create_referral_links(users, channel)
            set_links = set(channel_links.values())
            self.assertEqual(len(channel_links), len(set_links), 'There are duplicated links between users')
            check_already_created = job.search_or_create_referral_links(users, channel)
            # check the consistency of the links
            for user, link in channel_links.items():
                self.assertEqual(
                    link, check_already_created[user],
                    'The link is not the same')
            links_by_user_by_channel[channel] = channel_links
            links += links_by_user_by_channel[channel].values()
        # check the uniqueness of the links between channel
        all_links_set = set(links)
        self.assertEqual(len(links), len(all_links_set), 'There are duplicated links between channel')
        # check if no new link have been created
        job_url = url_join(job.get_base_url(), (job.website_url or '/jobs'))
        trackers = self.env['link.tracker'].search(
            [('url', '=', job_url), ('campaign_id', '=', job.utm_campaign_id.id)])
        self.assertEqual(len(trackers), len(all_links_set), 'There are new links created')

    def test_referral_campaign_tour(self):
        job = self.env['hr.job'].create({
            'name': 'Test Job Referral Campaign',
            'no_of_recruitment': '5',
            'company_id': self.company_1.id,
            'is_published': True,
        })
        self.env['hr.employee'].create([
            {
                'name': 'Steve employee',
                'company_id': self.company_1.id,
                'user_id': self.steve_user.id
            }, {
                'name': 'Richard employee',
                'company_id': self.company_1.id,
                'user_id': self.richard_user.id
            }, {
                'name': 'Employee without user',
                'company_id': self.company_1.id,
            },
        ])
        self.steve_user.email = 'steve.employee@company_test.com'
        self.richard_user.email = 'richard.employee@company_test.com'
        self.steve_user.groups_id |= self.env.ref("hr_recruitment.group_hr_recruitment_manager")

        self.assertFalse(job.utm_campaign_id)
        self.steve_user.write({
            'company_ids': [(4, self.company_1.id)],
            'company_id': self.company_1.id,
        })
        self.start_tour("/odoo", 'hr_referral_utm_campaign_tour', login="stv")

        self.assertTrue(job.utm_campaign_id.id)
        nb_trackers = self.env['link.tracker'].search_count([('campaign_id', '=', job.utm_campaign_id.id)])
        nb_employee_with_user = self.env['hr.employee'].search_count([
            ('user_id', '!=', False),
            ('company_id', '=', self.company_1.id)
        ])
        self.assertEqual(nb_trackers, nb_employee_with_user)
