# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('mass_mailing', 'post_install', '-at_install')
class TestMailingTrackingRestrictions(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contacts = cls.env['mailing.contact'].create([
            {'name': 'Manard', 'email': 'manard@yahoo.fr', 'country_id': cls.env.ref('base.fr').id},
            {'name': 'Max Cavalera', 'email': 'sepultura@appbarber.com.br', 'country_id': cls.env.ref('base.br').id},
        ])
        cls.contact_fr, cls.contact_br = cls.contacts

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_tracking_restrictions(self):
        country_fr = self.env.ref('base.fr')
        for no_open, no_click, countries, open_tracked, click_tracked in [
            (False, False, [], self.contacts, self.contacts),
            (True, False, [], self.env['mailing.contact'], self.contacts),
            (False, True, [], self.contacts, self.env['mailing.contact']),
            (True, True, country_fr.ids, self.contact_br, self.contact_br),
            (False, True, country_fr.ids, self.contacts, self.contact_br),
        ]:
            with self.subTest(no_open=no_open, no_click=no_click, countries=countries):
                mailing = self.env['mailing.mailing'].create({
                    'body_html': '<p>Hello <a id="url0" href="https://www.example.com">Odoo</a></p>',
                    'mailing_model_id': self.env['ir.model']._get('mailing.contact').id,
                    'mailing_domain': f"[('id', 'in', {self.contacts.ids})]",
                    'name': 'TrackingMailing',
                    'subject': 'Tracking',
                    'disable_open_tracking': no_open,
                    'disable_click_tracking': no_click,
                    'blacklisted_country_ids': [(6, 0, countries)],
                })
                with self.mock_mail_gateway(mail_unlink_sent=False):
                    mailing.action_send_mail()

                self.assertMailTraces(
                    [{'email': contact.email} for contact in self.contacts],
                    mailing, self.contacts,
                    check_mail=False,
                )
                for contact in self.contacts:
                    body = self._find_sent_mail_wemail(contact.email)['body']
                    # links: shortened (with the trace id) only for click-tracked recipients
                    href = self._get_href_from_anchor_id(body, 'url0')
                    if contact in click_tracked:
                        self.assertIn('/r/', href)
                        self.assertIn('/m/', href)
                    else:
                        self.assertEqual(href, 'https://www.example.com')
                    # opening pixel: added only for open-tracked recipients
                    if contact in open_tracked:
                        self.assertIn('blank.gif', body)
                    else:
                        self.assertNotIn('blank.gif', body)
                    mail = self.env['mail.mail'].sudo().search([
                        ('mailing_id', '=', mailing.id), ('email_to', '=', contact.email),
                    ])
                    self.assertEqual(mail.block_open_tracking, contact not in open_tracked)
                    self.assertEqual(mail.block_click_tracking, contact not in click_tracked)


@tagged('mass_mailing', 'post_install', '-at_install')
class TestMailingTrackingSettings(MassMailCommon):

    def _create_mailing(self):
        return self.env['mailing.mailing'].create({
            'name': 'Defaults',
            'subject': 'Defaults',
            'mailing_model_id': self.env['ir.model']._get('mailing.contact').id,
        })

    def test_restrict_mail_tracking_toggle(self):
        """ Turning the restriction toggle off resets the mailing defaults. """
        country_fr = self.env.ref('base.fr')
        self.env['res.config.settings'].create({
            'restrict_mail_tracking': True,
            'default_disable_open_tracking': True,
            'default_disable_click_tracking': True,
            'default_blacklisted_country_ids': [(6, 0, country_fr.ids)],
        }).execute()
        mailing = self._create_mailing()
        self.assertTrue(mailing.disable_open_tracking)
        self.assertTrue(mailing.disable_click_tracking)
        self.assertEqual(mailing.blacklisted_country_ids, country_fr)

        self.env['res.config.settings'].create({'restrict_mail_tracking': False}).execute()
        mailing = self._create_mailing()
        self.assertFalse(mailing.disable_open_tracking)
        self.assertFalse(mailing.disable_click_tracking)
        self.assertFalse(mailing.blacklisted_country_ids)
