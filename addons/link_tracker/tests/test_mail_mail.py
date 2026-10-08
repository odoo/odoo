from odoo.addons.mail.tests.common import MailCommon


class TestMailMail(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['link.tracker'].search([]).unlink()
        cls.tracked_link = cls.env['link.tracker'].create({
            'url': 'http://sepultura.brazil/chaos_ad/territory.mp3',
        })
        cls.br_partner = cls.env['res.partner'].create({
            'name': 'Max Cavalera',
            'email': 'max.cavalera@gmail.br',
            'country_id': cls.env['res.country'].search([('code', '=', 'BR')]).id,
        })
        cls.fr_partner = cls.env['res.partner'].create({
            'name': 'Manard',
            'email': 'manard@gmail.fr',
            'country_id': cls.env['res.country'].search([('code', '=', 'FR')]).id,
        })

    def test_disabled_link_tracking(self):
        """
            Testing the new system parameter that allows users to disable the link tracking feature when needed.
            As per the new legislation ordered by some countries.
        """
        code = self.tracked_link.code
        with self.mock_mail_gateway():
            self.fr_partner.message_post(body=f'Hello, look at {self.fr_partner.get_base_url()}/r/{code}', partner_ids=self.fr_partner.ids)
        mail_sent = self._find_sent_mail_wemail(self.fr_partner.email_formatted)
        self.assertIn(f'/r/{code}', mail_sent.get('body'))
        self.env['ir.config_parameter'].set_param('link_tracker.disable_link_tracking', 'FR')
        with self.mock_mail_gateway():
            self.fr_partner.message_post(body=f'Hello, look at {self.fr_partner.get_base_url()}/r/{code}', partner_ids=self.fr_partner.ids)
            self.br_partner.message_post(body=f'Hello, look at {self.br_partner.get_base_url()}/r/{code}', partner_ids=self.br_partner.ids)
        fr_mail_sent = self._find_sent_mail_wemail(self.fr_partner.email_formatted)
        br_mail_sent = self._find_sent_mail_wemail(self.br_partner.email_formatted)
        self.assertIn('http://sepultura.brazil/chaos_ad/territory.mp3', fr_mail_sent.get('body'))
        self.assertIn(f'/r/{code}', br_mail_sent.get('body'))
        self.env['ir.config_parameter'].set_param('link_tracker.disable_link_tracking', 'FR,BR')
        with self.mock_mail_gateway():
            self.fr_partner.message_post(body=f'Hello, look at {self.fr_partner.get_base_url()}/r/{code}', partner_ids=self.fr_partner.ids)
            self.br_partner.message_post(body=f'Hello, look at {self.br_partner.get_base_url()}/r/{code}', partner_ids=self.br_partner.ids)
        fr_mail_sent = self._find_sent_mail_wemail(self.fr_partner.email_formatted)
        br_mail_sent = self._find_sent_mail_wemail(self.br_partner.email_formatted)
        self.assertIn('http://sepultura.brazil/chaos_ad/territory.mp3', fr_mail_sent.get('body'))
        self.assertNotIn(f'/r/{code}', br_mail_sent.get('body'))
