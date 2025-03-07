from odoo.tests import TransactionCase, tagged, users
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('post_install', '-at_install')
class TestLinkTracker(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_1 =  cls.env.company

        cls.company_2 = cls.env['res.company'].create({
            'name': 'Company 2',
        })

        cls.website_1, cls.website_2 = cls.env['website'].create([
            {
                'name': 'website 1',
                'domain': 'https://maincompany.odoo.com',
                'company_id': cls.company_1.id
            },
            {
                'name': 'Website 2',
                'domain': 'https://secondarycompany.odoo.com',
                'company_id': cls.company_2.id
            }
        ])

        cls.company_1.write({'website_id': cls.website_1.id})

        cls.test_user = mail_new_test_user(
            cls.env,
            login='test_user',
            name='Test User',
            company_id=cls.company_1.id,
            company_ids=[(6, 0, [cls.company_1.id, cls.company_2.id])],
            groups="website.group_website_designer,base.group_user"
        )

    @users('test_user')
    def test_compute_short_url_host(self):
        """Test _compute_short_url_host with multiple companies/websites
            The short URL base should match the website domain of the company
        """
        link_1 = self.env['link.tracker'].create({
            'url': 'https://www.1odoo.com',
        })
        self.assertTrue(link_1.short_url.startswith(self.website_1.domain),
            "Short URL should use company 1 website domain")

        # Switch to Company 2
        self.env.user.company_id = self.company_2
        link_2 = self.env['link.tracker'].create({
            'url': 'https://www.2odoooo.com',
        })
        self.assertTrue(link_2.short_url.startswith(self.website_2.domain),
            "Short URL should use company 2 website domain"
        )

        # Remove website from Company 2
        # The short URL host should fallback to a default value
        self.company_2.write({'website_id': False})
        link_3 = self.env['link.tracker'].create({
            'url': 'https://www.3ooddoooo.com'
        })
        self.assertTrue(
            link_3.short_url_host,
            "Short URL host should have a fallback value when no website is configured"
        )
