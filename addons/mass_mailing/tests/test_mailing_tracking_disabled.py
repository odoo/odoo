# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('mass_mailing', 'post_install', '-at_install')
class TestMailingTrackingDisabled(MassMailCommon):
    """ Tracking (opening pixel, link shortening) may be disabled using the
    'mass_mailing.disable_tracking' system parameter, either globally or for
    recipients of some countries (e.g. France, Italy: tracking not allowed
    without prior consent). """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contacts = cls.env['mailing.contact'].create([{'name': 'Manard', 'email': 'manard@yahoo.fr', 'country_id': cls.env.ref('base.fr').id}, {'name': 'Max Cavalera', 'email': 'sepultura@appbarber.com.br', 'country_id': cls.env.ref('base.br').id}])
        cls.contact_fr, cls.contact_br = cls.contacts

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_tracking_disabled(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        for param_value, tracked_contacts in [
            (False, self.contacts),
            ('True', self.env['mailing.contact']),
            ('FR', self.contact_br),
        ]:
            with self.subTest(system_parameter_value=param_value):
                IrConfig.set_param('mass_mailing.disable_tracking', param_value)
                mailing = self.env['mailing.mailing'].create({
                    'body_html': '<p>Hello <a id="url0" href="https://www.example.com">Odoo</a></p>',
                    'mailing_model_id': self.env['ir.model']._get('mailing.contact').id,
                    'mailing_domain': f"[('id', 'in', {self.contacts.ids})]",
                    'name': 'TrackingMailing',
                    'subject': 'Tracking',
                })
                with self.mock_mail_gateway():
                    mailing.action_send_mail()

                # links: shortened only for tracked recipients
                self.assertMailTraces(
                    [{'email': contact.email} for contact in self.contacts],
                    mailing, self.contacts,
                    mail_links_info=[
                        [('url0', 'https://www.example.com', contact in tracked_contacts, {})]
                        for contact in self.contacts
                    ],
                    check_mail=False,
                )
                # opening pixel: added only for tracked recipients
                for contact in self.contacts:
                    body = self._find_sent_mail_wemail(contact.email)['body']
                    if contact in tracked_contacts:
                        self.assertIn('blank.gif', body)
                    else:
                        self.assertNotIn('blank.gif', body)
                if not tracked_contacts:
                    self.assertFalse(
                        self.env['link.tracker'].sudo().search_count([('mass_mailing_id', '=', mailing.id)]),
                        'No link tracker should be created when tracking is fully disabled',
                    )
