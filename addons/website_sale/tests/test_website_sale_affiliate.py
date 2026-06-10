# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleAffiliate(WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.affiliate_user = cls._create_new_internal_user(login='affiliate_user')
        cls.salesperson_user = cls._create_new_internal_user(login='salesperson_user')
        cls.partner_user = cls._create_new_internal_user(login='partner_user')
        cls.parent_partner_user = cls._create_new_internal_user(login='parent_partner_user')

    def test_affiliate_id_in_session_is_used_as_salesperson(self):
        """ When a valid affiliate id is stored in the session, it takes
        precedence over the website salesperson and the partner's
        salesperson. """
        self.website.salesperson_id = self.salesperson_user
        self.partner.user_id = self.partner_user

        with MockRequest(self.env, website=self.website) as request:
            request.session['affiliate_id'] = self.affiliate_user.id
            values = self.website._prepare_sale_order_values(self.partner)

        self.assertEqual(values['user_id'], self.affiliate_user.id)

    def test_unknown_affiliate_id_falls_back_to_website_salesperson(self):
        """ When the affiliate id stored in the session doesn't match any
        user, the website salesperson is used instead. """
        self.website.salesperson_id = self.salesperson_user
        self.partner.user_id = self.partner_user

        with MockRequest(self.env, website=self.website) as request:
            request.session['affiliate_id'] = self.env['res.users'].search(
                [], order='id desc', limit=1
            ).id + 1000
            values = self.website._prepare_sale_order_values(self.partner)

        self.assertEqual(values['user_id'], self.salesperson_user.id)

    def test_no_affiliate_id_falls_back_to_website_salesperson(self):
        """ When no affiliate id is stored in the session, the website
        salesperson is used. """
        self.website.salesperson_id = self.salesperson_user
        self.partner.user_id = self.partner_user

        with MockRequest(self.env, website=self.website) as request:
            values = self.website._prepare_sale_order_values(self.partner)

        self.assertEqual(values['user_id'], self.salesperson_user.id)

    def test_no_affiliate_no_website_salesperson_falls_back_to_partner_user(self):
        """ When neither an affiliate nor a website salesperson is set, the
        partner's own salesperson is used. """
        self.website.salesperson_id = False
        self.partner.user_id = self.partner_user

        with MockRequest(self.env, website=self.website) as request:
            values = self.website._prepare_sale_order_values(self.partner)

        self.assertEqual(values['user_id'], self.partner_user.id)

    def test_no_affiliate_no_salesperson_falls_back_to_parent_partner_user(self):
        """ When neither an affiliate, a website salesperson, nor the
        partner's own salesperson is set, the parent partner's salesperson
        is used. """
        self.website.salesperson_id = False
        self.partner.user_id = False
        self.partner.parent_id = self.env['res.partner'].create({
            'name': "Parent Partner",
            'user_id': self.parent_partner_user.id,
        })

        with MockRequest(self.env, website=self.website) as request:
            values = self.website._prepare_sale_order_values(self.partner)

        self.assertEqual(values['user_id'], self.parent_partner_user.id)

    def test_create_cart_with_affiliate(self):
        """ The affiliate stored in the session is set as the salesperson of
        the cart created on the website. """
        with MockRequest(self.env(user=self.public_user), website=self.website) as request:
            request.session['affiliate_id'] = self.affiliate_user.id
            order = request.website._create_cart()

        self.assertEqual(order.user_id, self.affiliate_user)