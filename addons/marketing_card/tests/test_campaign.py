import base64
from lxml import html
from unittest.mock import patch

from odoo import exceptions
from odoo.tools import mute_logger
from odoo.tests.common import users
from odoo.tests import Form, HttpCase, tagged, warmup
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.marketing_card.controllers.marketing_card import SOCIAL_NETWORK_USER_AGENTS

from .common import MarketingCardCommon, mock_image_render, VALID_JPEG


def _extract_values_from_document(rendered_document):
    return {
        'body': rendered_document.find('.//div[@id="body"]'),
        'header': rendered_document.find('.//span[@id="header"]'),
        'subheader': rendered_document.find('.//span[@id="subheader"]'),
        'section': rendered_document.find('.//span[@id="section"]'),
        'sub_section1': rendered_document.find('.//span[@id="sub_section1"]'),
        'sub_section2': rendered_document.find('.//span[@id="sub_section2"]'),
        'button': rendered_document.find('.//span[@id="button"]'),
        'image1': rendered_document.find('.//img[@id="image1"]'),
        'image2': rendered_document.find('.//img[@id="image2"]'),
    }


class TestMarketingCardMail(MailCase, MarketingCardCommon):

    @users('marketing_card_user')
    @warmup
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_campaign_send_mailing(self):
        campaign = self.campaign.with_user(self.env.user)
        self.env.user.sudo().groups_id += self.env.ref('mass_mailing.group_mass_mailing_user')
        partners = self.env['res.partner'].sudo().create([{'name': f'Part{n}', 'email': f'partn{n}@test.lan'} for n in range(7)])
        mailing_context = campaign.action_share().get('context') | {
            'default_email_from': 'test@test.lan',
            'default_mailing_domain': [('id', 'in', partners.ids[:5])],
            'default_reply_to': 'test@test.lan',
        }
        mailing = Form(self.env['mailing.mailing'].with_context(mailing_context)).save()
        mailing.body_html = mailing.body_arch  # normally the js html_field would fill this in

        # sending mailing before generating cards sends to no-one
        self.assertTrue(mailing.card_requires_sync_count)
        with self.assertRaises(exceptions.UserError, msg="There are no recipients selected."):
            mailing._action_send_mail()

        with self.assertRaises(exceptions.UserError, msg="You should update all the cards before scheduling a mailing."):
            mailing.action_launch()

        # once cards are updated they can be sent
        with self.mock_image_renderer():
            mailing.action_update_cards()
        self.assertEqual(len(self._wkhtmltoimage_bodies), 5)

        self.assertFalse(mailing.card_requires_sync_count)
        mailing.action_launch()
        mailing.action_cancel()

        # modifying the domain such that there are missing cards prevents sending again
        mailing.mailing_domain = [('id', 'in', partners.ids[1:6])]
        mailing._compute_card_requires_sync_count()
        self.assertTrue(mailing.card_requires_sync_count)
        with self.assertRaises(exceptions.UserError, msg="You should update all the cards before scheduling a mailing."):
            mailing.action_launch()

        # updating when the campaign was not modified only updates cards that need to be
        with self.mock_image_renderer():
            mailing.action_update_cards()
        self.assertEqual(len(self._wkhtmltoimage_bodies), 1)

        self.assertFalse(mailing.card_requires_sync_count)

        # modifying the campaign should lead to all cards relevant being re-rendered
        campaign.content_header = "New Header"
        mailing._compute_card_requires_sync_count()
        self.assertTrue(mailing.card_requires_sync_count)
        with self.mock_image_renderer():
            mailing.action_update_cards()
        self.assertEqual(len(self._wkhtmltoimage_bodies), 5)

        with self.mock_mail_gateway(), self.assertQueryCount(243):
            mailing._action_send_mail()

        cards = self.env['card.card'].search([('campaign_id', '=', campaign.id)])
        self.assertEqual(len(cards), 6)
        self.assertEqual(len(cards.filtered(lambda card: not card.requires_sync)), 5)
        self.assertEqual(len(self._mails), 5)

        IrHttp = self.env['ir.http']
        for sent_mail in self._mails:
            record_id = int(sent_mail['object_id'].split('-')[0])
            card = cards.filtered(lambda card: card.res_id == record_id)
            self.assertEqual(len(card), 1)
            preview_url = f"{campaign.get_base_url()}/cards/{IrHttp._slug(card)}/preview"
            image_url = f"{campaign.get_base_url()}/cards/{IrHttp._slug(card)}/card.jpg"
            self.assertIn(f'<a href="{preview_url}"', sent_mail['body'])
            self.assertIn(f'<img src="{image_url}"', sent_mail['body'])


class TestMarketingCardRender(MarketingCardCommon):

    @users('marketing_card_user')
    def test_campaign(self):
        campaign = self.campaign.with_user(self.env.user)

        with self.mock_image_renderer():
            campaign.write({
                'content_header': 'Come and See',
                'content_header_dyn': False,
                'content_header_color': '#CC8888',
            })
            self.assertTrue(campaign.image_preview)

        role_values = _extract_values_from_document(html.fromstring(self._wkhtmltoimage_bodies[0]))
        self.assertEqual(role_values['body'].attrib['style'], "background-image: url('data:image/png;base64,');")
        self.assertEqual(role_values['header'].text, 'Come and See')
        self.assertEqual(role_values['header'].attrib['style'], 'color: #CC8888;')
        self.assertEqual(role_values['subheader'].text, 'John')
        self.assertEqual(role_values['section'].text, 'Contact')
        self.assertEqual(role_values['sub_section1'].text, 'john93@trombino.scope')
        self.assertFalse(role_values['sub_section2'])
        self.assertEqual(role_values['button'].text, 'Button')
        self.assertFalse(role_values['image1'])
        self.assertFalse(role_values['image2'])

        campaign.action_preview()
        card = self.env['card.card'].search([
            ('campaign_id', '=', campaign.id),
            ('active', '=', False)
        ])
        self.assertEqual(len(card), 1)
        self.assertTrue(card.image)
        self.assertEqual(card.res_id, self.partners[0].id)

        # second record, modified tags

        with self.mock_image_renderer():
            campaign.preview_record_ref = self.partners[1]
            self.assertTrue(campaign.image_preview)
        role_values = _extract_values_from_document(html.fromstring(self._wkhtmltoimage_bodies[0]))
        self.assertEqual(role_values['body'].attrib['style'], "background-image: url('data:image/png;base64,');")
        self.assertEqual(role_values['subheader'].text, 'Bob')
        self.assertEqual(role_values['sub_section1'].text, 'bob@justbob.me')
        self.assertEqual(role_values['sub_section2'].text, '+32 123 446 789')
        self.assertFalse(role_values['image1'])
        self.assertEqual(role_values['image2'].attrib['src'], f'data:image/png;base64,{base64.b64encode(VALID_JPEG).decode()}')

        campaign.action_preview()
        cards = self.env['card.card'].search([
            ('campaign_id', '=', campaign.id),
            ('active', '=', False)
        ])
        self.assertTrue(cards.mapped('res_id'), self.partners.ids)

        # update previewed record fields

        with self.mock_image_renderer():
            campaign.preview_record_ref.sudo().name = 'An updated name'
        self.assertFalse(self._wkhtmltoimage_bodies, 'Updating the preview record does not refresh the preview.')

        # mismatch preview

        with patch('odoo.addons.marketing_card.models.card_campaign.CardCampaign._get_model_selection',
                   lambda Model: [('res.partner', 'Partner'), ('res.users', 'User')]):

            # mismatches without cards
            self.assertEqual(self.static_campaign.res_model, 'res.partner')
            self.assertFalse(self.static_campaign.card_ids)
            self.static_campaign.preview_record_ref = self.env.user
            self.assertEqual(self.static_campaign.res_model, 'res.users')
            self.static_campaign.preview_record_ref = self.partners[1]
            self.assertEqual(self.static_campaign.res_model, 'res.partner')

            # mismatch with card
            self.env['card.card'].sudo().create({'campaign_id': self.static_campaign.id, 'res_id': 1})

            self.assertTrue(self.static_campaign.card_ids)
            with self.assertRaises(exceptions.ValidationError):
                self.static_campaign.preview_record_ref = self.env.user
                self.assertTrue(self.static_campaign.res_model)
            self.assertEqual(self.static_campaign.res_model, 'res.partner')

            # match with card
            self.static_campaign.preview_record_ref = self.partners[0]
            self.assertEqual(self.static_campaign.res_model, 'res.partner')


@tagged('post_install', '-at_install')
class TestMarketingCardRouting(HttpCase, MarketingCardCommon):

    @mock_image_render
    def test_campaign_stats(self):
        partners = self.env['res.partner'].create([{'name': f'Part{n}', 'email': f'partn{n}@test.lan'} for n in range(20)])
        cards = self.campaign._update_cards([('id', 'in', partners.ids)]).sorted('res_id')
        self.assertEqual(len(cards), 20)
        self.assertEqual(self.campaign.card_count, 20)
        self.assertEqual(self.campaign.card_click_count, 0)
        self.assertEqual(self.campaign.card_share_count, 0)
        self.assertListEqual(cards.mapped('image'), [base64.b64encode(VALID_JPEG)] * 20)
        self.assertListEqual(cards.mapped('share_status'), [False] * 20)
        self.assertListEqual(cards.mapped('requires_sync'), [False] * 20)

        # user checks preview
        self.campaign.preview_record_ref = partners[0]
        card = cards.filtered(lambda card: card.res_id == partners[0].id)
        self.assertEqual(self.campaign.action_preview()['url'], card._get_path('preview'))
        self.url_open(card._get_path('preview'))
        image_request_headers = self.url_open(card._get_card_url()).headers
        self.assertEqual(image_request_headers.get('Content-Type'), 'image/jpeg')
        self.assertTrue(image_request_headers.get('Content-Length'))
        self.assertTrue(card.image)
        self.assertEqual(card.share_status, 'visited')
        self.campaign.flush_recordset()
        self.assertEqual(self.campaign.card_count, 20)
        self.assertEqual(self.campaign.card_click_count, 1)
        self.assertEqual(self.campaign.card_share_count, 0, 'A regular user fetching the card should not count as a share.')

        # user publishes redirect url, prompting social network crawler to check open-graph data
        self.opener.headers['User-Agent'] = f'v1 {SOCIAL_NETWORK_USER_AGENTS[0]} v1.2/'
        opengraph_view = html.fromstring(self.url_open(card._get_redirect_url()).content)
        self.assertTrue(opengraph_view is not None, 'Crawler should get a valid html page as response')
        opengraph_image_url_element = opengraph_view.find('.//meta[@property="og:image"]')
        self.assertTrue(opengraph_image_url_element is not None, 'page should contain image opengraph node')
        opengraph_image_url = opengraph_image_url_element.attrib.get('content')
        self.assertTrue(opengraph_image_url)
        self.assertEqual(opengraph_image_url, card._get_card_url())

        image_request_headers = self.url_open(opengraph_image_url).headers
        self.assertEqual(image_request_headers.get('Content-Type'), 'image/jpeg')
        self.assertTrue(image_request_headers.get('Content-Length'))

        self.campaign.flush_recordset()
        self.assertEqual(self.campaign.card_count, 20)
        self.assertEqual(self.campaign.card_click_count, 1)
        self.assertEqual(self.campaign.card_share_count, 1, "A crawler fetching the card is considered a share.")
        self.assertEqual(cards[0].share_status, 'shared')

        # someone clicks the redirect url on the social network platform
        self.assertEqual(self.campaign.target_url_click_count, 0)
        self.opener.headers['User-Agent'] = 'someuseragent'
        redirect_response = self.url_open(card._get_redirect_url(), allow_redirects=False)
        self.assertEqual(redirect_response.status_code, 303)
        self.assertEqual(redirect_response._next.url, self.campaign.link_tracker_id.short_url)
        self.opener.send(redirect_response._next, allow_redirects=False)
        self.assertEqual(self.campaign.target_url_click_count, 1)

        cards[1:10].share_status = 'visited'
        cards[10:].share_status = 'shared'
        self.assertEqual(self.campaign.card_count, 20)
        self.assertEqual(self.campaign.card_click_count, 20, 'Shared cards are considered implicitly visited')
        self.assertEqual(self.campaign.card_share_count, 11)


class TestMarketingCardSecurity(MarketingCardCommon):

    @users('marketing_card_manager')
    @mute_logger('odoo.addons.mail.models.mail_render_mixin')
    def test_campaign_field_paths(self):
        """Check that card updates are performed as the current user."""
        # restrict reading from partner titles (flush to apply new rule)
        rules = self.env['ir.rule'].sudo().create([{
            'name': 'marketing card user read partner title',
            'domain_force': repr([(0, '=', 1)]),
            'groups': self.env.ref('marketing_card.marketing_card_group_user').ids,
            'model_id': self.env['ir.model']._get_id('res.partner.title'),
            'perm_read': True,
        }, {
            'name': 'system user read partner title',
            'domain_force': repr([(1, '=', 1)]),
            'groups': self.env.ref('base.group_system').ids,
            'model_id': self.env['ir.model']._get_id('res.partner.title'),
            'perm_read': True,
        }])
        rules.flush_recordset()
        # set a title as sudo and invalidate to force fetch as test user
        self.marketing_card_user.partner_id.title = self.env['res.partner.title'].sudo().create({
            'name': 'test marketing card title',
        })
        self.marketing_card_user.partner_id.title.invalidate_recordset()

        campaign = self.campaign.with_user(self.env.user)
        campaign.preview_record_ref = self.marketing_card_user.partner_id
        # should work fine with accessible fields
        campaign._update_cards([('id', '=', self.marketing_card_user.partner_id.id)])
        with self.assertRaises(exceptions.UserError):
            campaign.write({
                'content_header_dyn': True,
                'content_header_path': 'title.name',
            })
            # flush to compute image_preview
            campaign.flush_recordset()

        campaign.with_user(self.system_admin).write({
            'content_header_dyn': True,
            'content_header_path': 'title.name',
        })
        campaign.with_user(self.system_admin).flush_recordset()
        # clear title from cache as it was fetched by the admin for the preview render
        self.marketing_card_user.partner_id.title.invalidate_recordset()

        with self.assertRaises(exceptions.UserError), self.mock_image_renderer():
            campaign._update_cards([('id', '=', self.marketing_card_user.partner_id.id)])
        self.assertFalse(self._wkhtmltoimage_bodies, 'There should have been no render on illegal fields')

        with self.mock_image_renderer():
            campaign.with_user(self.system_admin)._update_cards([('id', '=', self.marketing_card_user.partner_id.id)])
        self.assertIn('test marketing card title', self._wkhtmltoimage_bodies[0])

    def test_campaign_ownership(self):
        campaign_as_manager = self.campaign.with_user(self.marketing_card_manager)
        campaign_as_owner = self.campaign.with_user(self.marketing_card_user)
        campaign_as_other = self.campaign.with_user(self.marketing_card_user_2)

        with self.assertRaises(exceptions.AccessError):
            campaign_as_other.content_header = 'Hello'
        campaign_as_owner.content_header = 'Hi'
        campaign_as_manager.content_header = 'Hoy'

        with self.assertRaises(exceptions.AccessError):
            campaign_as_other.unlink()
        campaign_as_owner.unlink()
