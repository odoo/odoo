# -*- coding: utf-8 -*-
import requests

from odoo.api import Environment
from odoo.tests import common

class TestConfirmUnsubscribe(common.HttpCase):
    def setUp(self):
        super(TestConfirmUnsubscribe, self).setUp()

        cr = self.registry.cursor()
        # apparently HttpCase does not properly update self.env?
        self.env2 = env = Environment(cr, self.uid, {})
        self.partner = env['res.partner'].create({
            'name': 'Bob',
            'email': 'bob@bob.bob'
        })
        self.mailing_list = env['mail.channel'].create({
            'name': 'Test Mailing List',
            'public': 'public',
        })
        self.token = self.mailing_list._generate_action_token(self.partner.id, action='unsubscribe')

    def test_not_subscribed(self):
        """Test warning works"""
        self.env2.cr.release()

        self._unsubscribe_check("The address %s is already unsubscribed" % self.partner.email)

    def test_not_subscribed_no_template(self):
        """ Test warning works on db without template (code update w/o module update) """
        self.env2.ref('website_mail_channel.not_subscribed').unlink()
        self.assertEquals(
            self.env2['ir.model.data'].search_count([
            ('module', '=', 'website_mail_channel'),
            ('name', '=', 'not_subscribed'),
        ]), 0, 'XID for template should have been deleted')
        self.env2.cr.release()

        self._unsubscribe_check("The address %s is already unsubscribed or was never subscribed to any mailing list" % self.partner.email)

    def test_wrong_token(self):
        self.mailing_list.sudo().write({
            'channel_partner_ids': [(4, self.partner.id, False)]
        })
        self.env2.cr.release()
        self.token = 'XXX'

        self._unsubscribe_check("Invalid or expired confirmation link.")

    def test_successful_unsubscribe(self):
        self.mailing_list.sudo().write({
            'channel_partner_ids': [(4, self.partner.id, False)]
        })
        self.env2.cr.release()

        self._unsubscribe_check("You have been correctly unsubscribed")

    def _unsubscribe_check(self, text):
        url = "http://{}:{}/groups/unsubscribe/{}/{}/{}".format(
            common.HOST, common.PORT,
            self.mailing_list.id, self.partner.id,
            self.token
        )
        r = requests.get(url)
        r.raise_for_status()
        body = r.text
        # normalize space to make matching simpler
        self.assertIn(text, u' '.join(body.split()))
