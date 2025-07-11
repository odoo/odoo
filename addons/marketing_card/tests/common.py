import base64
from contextlib import contextmanager
from freezegun import freeze_time
from unittest.mock import patch

from odoo.tests import BaseCase, TransactionCase
from odoo.addons.base.models.ir_actions_report import IrActionsReport
from odoo.addons.mail.tests.common import mail_new_test_user


VALID_JPEG = base64.b64decode('/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/yQALCAABAAEBAREA/8wABgAQEAX/2gAIAQEAAD8A0s8g/9k=')


def mock_image_render(func):
    def patched(self, *args, **kwargs):
        with self.mock_image_renderer(collect_params=False):
            return func(self, *args, **kwargs)
    return patched


class MockImageRender(BaseCase):
    @contextmanager
    def mock_image_renderer(self, collect_params=True):
        self._wkhtmltoimage_bodies = []

        def _ir_actions_report_build_run_wkhtmltoimage(model, bodies, width, height, image_format="jpg"):
            if collect_params:
                self._wkhtmltoimage_bodies.extend(bodies)
            return [VALID_JPEG] * len(bodies)

        with patch.object(IrActionsReport, '_run_wkhtmltoimage', _ir_actions_report_build_run_wkhtmltoimage):
            yield


class MarketingCardCommon(TransactionCase, MockImageRender):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env['res.company'].create({
            'country_id': cls.env.ref("base.be").id,
            'email': 'your.company@example.',
            'name': 'YourTestCompany',
        })
        cls.marketing_card_manager = mail_new_test_user(
            cls.env,
            company_id=cls.company.id,
            email='manager.marketing.card@example.com',
            login='marketing_card_manager',
            groups='marketing_card.marketing_card_group_manager',
            name='Marketing Card Manager',
        )
        cls.marketing_card_user = mail_new_test_user(
            cls.env,
            company_id=cls.company.id,
            email='user.marketing.card@example.com',
            login='marketing_card_user',
            groups='marketing_card.marketing_card_group_user',
            name='Marketing Card User',
        )
        cls.marketing_card_user_2 = cls.marketing_card_user.copy({
            'email': 'user2.marketing.card@example.com',
            'login': 'marketing_card_user_2',
            'name': 'Marketing Card User 2',
        })
        cls.system_admin = mail_new_test_user(
            cls.env,
            company_id=cls.company.id,
            email='system.marketing.card@example.com',
            login='marketing_card_system_admin',
            groups='base.group_system,marketing_card.marketing_card_group_manager',
            name='System Admin',
        )

        cls.partners = cls.env['res.partner'].create([
            {'name': 'John', 'email': 'john93@trombino.scope'},
            {'name': 'Bob', 'email': 'bob@justbob.me',
             'phone': '+32 123 446 789', 'image_1920': base64.b64encode(VALID_JPEG),
             },
        ])

        cls.card_template = cls.env['card.template'].create({
            'name': 'Test Template',
            'body': """
<html>
    <t t-set="values" t-value="card_campaign._get_card_element_values(object)"/>
    <head>
        <style>
            p { margin: 1px };
            body { width: 100%; height: 100%; };
        </style>
    </head>
    <body>
    <div id="body" t-attf-style="background-image: url('data:image/png;base64,{{card_campaign.content_background or card_campaign.card_template_id.default_background}}');">
                <span id="header" t-out="values['header']" t-att-style="'color: %s;' % card_campaign.content_header_color"/>
                <span id="subheader" t-out="values['sub_header']" t-att-style="'color: %s;' % card_campaign.content_sub_header_color"/>
                <span id="button" t-out="card_campaign.content_button">Button</span>
                <span id="section" t-out="values['section']"/>
                <span id="sub_section1" t-out="values['sub_section1']"/>
                <span id="sub_section2" t-out="values['sub_section2']"/>
                <img id="image1" t-if="values['image1']" t-attf-src="data:image/png;base64,{{values['image1']}}"/>
                <img id="image2" t-if="values['image2']" t-attf-src="data:image/png;base64,{{values['image2']}}"/>
    </div>
    </body>
</html>
            """,
        })

        cls.campaign = cls.env['card.campaign'].with_user(cls.marketing_card_user).create({
            'name': 'Test Campaign',
            'card_template_id': cls.card_template.id,
            'post_suggestion': 'Come see my show!',
            'preview_record_ref': f'{cls.partners._name},{cls.partners[0].id}',
            'reward_message': """<p>Thanks for sharing!</p>""",
            'reward_target_url': f"{cls.env['card.campaign'].get_base_url()}/share-rewards/2039-sharer-badge/",
            'target_url': cls.env['card.campaign'].get_base_url(),
            'content_section': 'Contact',
            'content_sub_header_dyn': True,
            'content_sub_header_path': 'name',
            'content_sub_section1_dyn': True,
            'content_sub_section1_path': 'email',
            'content_sub_section2_dyn': True,
            'content_sub_section2_path': 'phone',
            'content_image1_path': 'user_ids.image_256',
            'content_image2_path': 'image_256',
        })
        cls.static_campaign = cls.env['card.campaign'].with_user(cls.marketing_card_user).create({
            'name': 'Simple Campaign',
            'card_template_id': cls.card_template.id,
            'post_suggestion': 'Come see my show!',
            'preview_record_ref': f'{cls.partners._name},{cls.partners[0].id}',
            'reward_message': """<p>Thanks for sharing!</p>""",
            'reward_target_url': f"{cls.env['card.campaign'].get_base_url()}/share-rewards/2039-sharer-badge/",
            'target_url': cls.env['card.campaign'].get_base_url(),
        })

    @contextmanager
    def mock_datetime_and_now(self, mock_dt):
        with freeze_time(mock_dt), \
                patch.object(self.env.cr, 'now', lambda: mock_dt):
            yield
