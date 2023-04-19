# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo.tests.common import users

from odoo.addons.mass_mailing.tests.common import MassMailCommon


class TestMassMailingWebsite(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailingWebsite, cls).setUpClass()
        website_1 = cls.env['website'].create({
            'name': 'Website 1',
            'domain': 'www.website1.com',
        })
        website_2 = cls.env['website'].create({
            'name': 'Website 2',
            'domain': 'www.website2.com',
        })
        body_html = """
            Test body
            <a role="button" href="/unsubscribe_from_list" class="btn btn-link ">Unsubscribe</a>
            <a href="/view" class="o_default_snippet_text">View Online</a>
            <a role="button" href="/contactus" class="btn btn-link">Contact</a>
        """
        mailing_list = cls._create_mailing_list_of_x_contacts(1)
        cls.mailing_1 = cls.env['mailing.mailing'].create({
            'name': 'Test Mailing 1',
            'subject': 'Test Subject 1',
            'body_html': body_html,
            'mailing_model_id': cls.env.ref('mass_mailing.model_mailing_list').id,
            'mailing_type': 'mail',
            'contact_list_ids': [mailing_list.id],
            'website_id': website_1.id,
        })
        cls.mailing_2 = cls.env['mailing.mailing'].create({
            'name': 'Test Mailing 2',
            'subject': 'Test Subject 2',
            'body_html': body_html,
            'mailing_model_id': cls.env.ref('mass_mailing.model_mailing_list').id,
            'mailing_type': 'mail',
            'contact_list_ids': [mailing_list.id],
            'website_id': website_2.id,
        })

    @users('user_marketing')
    def test_mass_mailing_website(self):

        def _assert_find_link(regex, mail):
            self.assertEqual(len(re.findall(regex, mail['body'])), 1)
            self.assertEqual(len(re.findall(regex, mail['body_alternative'])), 1)

        with self.mock_mail_gateway():
            (self.mailing_1 | self.mailing_2).action_send_mail()

        mail_1 = self._mails[0]
        unsubscribe_regex_1 = r'\bhttps?://(?:www\.)?website1\.com/.*?/unsubscribe\S*'
        view_regex_1 = r'\bhttps?://(?:www\.)?website1\.com/.*?/view\S*'
        contact_regex_1 = r'\bhttps?://(?:www\.)?website1\.com/r/\S*'

        mail_2 = self._mails[1]
        unsubscribe_regex_2 = r'\bhttps?://(?:www\.)?website2\.com/.*?/unsubscribe\S*'
        view_regex_2 = r'\bhttps?://(?:www\.)?website2\.com/.*?/view\S*'
        contact_regex_2 = r'\bhttps?://(?:www\.)?website2\.com/r/\S*'

        tracker_mailing_1 = self.env['link.tracker'].search([('mass_mailing_id', '=', self.mailing_1.id)])
        self.assertTrue('contactus' in tracker_mailing_1.url)
        self.assertTrue('website1' in tracker_mailing_1.short_url_host)
        tracker_mailing_2 = self.env['link.tracker'].search([('mass_mailing_id', '=', self.mailing_2.id)])
        self.assertTrue('contactus' in tracker_mailing_2.url)
        self.assertTrue('website2' in tracker_mailing_2.short_url_host)

        _assert_find_link(unsubscribe_regex_1, mail_1)
        _assert_find_link(view_regex_1, mail_1)
        _assert_find_link(contact_regex_1, mail_1)

        _assert_find_link(unsubscribe_regex_2, mail_2)
        _assert_find_link(view_regex_2, mail_2)
        _assert_find_link(contact_regex_2, mail_2)
