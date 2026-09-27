import lxml.html

from odoo.tests import Form, users

from odoo.addons.marketing_card.tests.common import MarketingCardCommon


class TestMarketingCardEventMailing(MarketingCardCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.marketing_card_user.group_ids += cls.env.ref('event.group_event_user')
        cls.ziggurat_event, cls.moon_event = cls.env['event.event'].create([
            {'name': 'Ziggurat Building Convention', 'company_id': False},
            {'name': 'Artemis II Conference', 'company_id': False},
        ])
        cls.ziggurat_registration, cls.moon_registration = cls.env['event.registration'].create([
            {'name': 'Gilgamesh', 'event_id': cls.ziggurat_event.id},
            {'name': 'G-man', 'event_id': cls.moon_event.id},
        ])

        cls.ziggurat_campaign = cls.static_campaign.copy({'name': 'Ziggurat Event'})
        cls.ziggurat_campaign.preview_record_ref = cls.ziggurat_registration
        cls.moon_campaign = cls.static_campaign.copy({'name': 'Moon Campaign'})
        cls.moon_campaign.preview_record_ref = cls.moon_registration

    @users('marketing_card_user')
    def test_picking_campaign_updates_domain(self):
        """Ensure the domain of the mailing matches the selected marketing campaign."""
        form_ctx = self.ziggurat_event.action_open_card_mailing()['context']
        mailing_form = Form(self.env['mailing.mailing'].with_context(form_ctx), 'marketing_card_event.mailing_mailing_view_form_event_send_card')

        self.assertEqual(mailing_form.mailing_domain, f"[('event_id', '=', {self.ziggurat_event.id}), ('state', 'not in', ['cancel', 'draft'])]")
        self.assertFalse(mailing_form.card_campaign_id)

        mailing_form.card_campaign_id = self.ziggurat_campaign
        self.assertEqual(
            mailing_form.mailing_domain,
            repr(['&', ('event_id', 'in', [self.ziggurat_event.id]), ('state', 'not in', ['cancel', 'draft'])]),
            'Selecting a campaign with the same event may normalize/optimize the domain.',
        )
        mailing_form.mailing_domain = [('event_id', 'in', [self.ziggurat_event.id]), ('create_date', '>', '2020-01-01')]

        mailing_form.card_campaign_id = self.moon_campaign
        self.assertEqual(
            mailing_form.mailing_domain,
            repr(['&', ('event_id', 'in', [self.ziggurat_event.id]), ('state', 'not in', ['cancel', 'draft'])]),
            'The event should be the one the cards are sent from, not the one of the campaign preview record.\n'
            'Only the event is kept, the rest of the domain is reset to the model default.'
        )

    @users('marketing_card_user')
    def test_picking_campaign_updates_body(self):
        """Ensure the card preview url matches the campaign.

        In the regular flow the card campaign is locked to readonly.
        Hence why this is tested here despite being a base module feature.
        """
        form_ctx = self.static_campaign.action_share()['context']
        mailing_form = Form(self.env['mailing.mailing'].with_context(form_ctx), 'marketing_card_event.mailing_mailing_view_form_event_send_card')

        # using lxml here helps ensure the structure is still valid html
        body_arch = lxml.html.fragment_fromstring(mailing_form.body_arch)
        image_element = body_arch.xpath("//img[@alt='Card Preview']")
        self.assertEqual(len(image_element), 1)
        self.assertEqual(image_element[0].attrib['src'], f'/web/image/card.campaign/{self.static_campaign.id}/image_preview')

        mailing_form.card_campaign_id = self.campaign
        body_arch = lxml.html.fragment_fromstring(mailing_form.body_arch)
        image_element = body_arch.xpath("//img[@alt='Card Preview']")
        self.assertEqual(len(image_element), 1)
        self.assertEqual(image_element[0].attrib['src'], f'/web/image/card.campaign/{self.campaign.id}/image_preview')

    @users('marketing_card_user')
    def test_sharing_campaign_updates_domain(self):
        """Ensure the domain matches the event of the campaign preview record when sharing from the campaign."""
        form_ctx = self.moon_campaign.action_share()['context']
        mailing_form = Form(self.env['mailing.mailing'].with_context(form_ctx), 'marketing_card_event.mailing_mailing_view_form_event_send_card')

        self.assertEqual(
            mailing_form.mailing_domain,
            repr(['&', ('event_id', '=', self.moon_event.id), ('state', 'not in', ['cancel', 'draft'])]),
            'The preview record event should be used as no event was given.',
        )
