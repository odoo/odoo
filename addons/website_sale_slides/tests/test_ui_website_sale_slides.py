# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, tests
from odoo.addons.website_slides.tests import test_ui_wslides


@tests.common.tagged('post_install', '-at_install')
class TestUiWebsiteSaleSlides(test_ui_wslides.TestUICommon):

    def setUp(self):
        super(TestUiWebsiteSaleSlides, self).setUp()
        self.course_product = self.env['product.product'].create({
            'name': "Course Product",
            'standard_price': 100,
            'list_price': 150,
            'type': 'service',
            'invoice_policy': 'order',
            'is_published': True,
        })

        self.channel.write({
            'enroll': 'payment',
            'product_id': self.course_product.id,
            'visibility': 'connected',
        })

        self.channel_partner_portal = self.env['slide.channel.partner'].create({
            'channel_id': self.channel.id,
            'partner_id': self.user_portal.partner_id.id,
            'member_status': 'invited',
            'last_invitation_date': fields.Datetime.now(),
        })
        self.portal_invite_url = self.channel_partner_portal.invitation_link

    def test_invited_on_payment_course_logged_connected(self):
        self.start_tour(self.portal_invite_url, 'invited_on_payment_course_logged', login='portal')

    def test_invited_on_payment_course_public_connected(self):
        self.start_tour(self.portal_invite_url, 'invited_on_payment_course_public', login=None)
