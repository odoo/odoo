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
            groups="website.group_website_designer"
        )

    @users('test_user')
    def test_compute_short_url_host(self):
        """The short URL host depends on the current website and company."""
        base_url = self.env['link.tracker'].get_base_url()

        # Current website matches the company's website.
        link_1 = self.env['link.tracker'].with_context(website_id=self.website_1.id).create({
            'url': 'https://www.1odoo.com',
        })
        self.assertTrue(link_1.short_url.startswith(self.website_1.domain),
            "Short URL uses the current website's domain")

        # Current website differs from the company's website.
        self.env.user.company_id = self.company_2
        link_2 = self.env['link.tracker'].with_context(website_id=self.website_1.id).create({
            'url': 'https://www.2odoooo.com',
        })
        self.assertTrue(link_2.short_url.startswith(self.website_2.domain),
            "Short URL uses the company's website domain when it differs from the current website")

        # No website resolvable from context.
        link_3 = self.env['link.tracker'].create({
            'url': 'https://www.3ooddoooo.com',
        })
        self.assertTrue(link_3.short_url.startswith(base_url),
            "Short URL uses web.base.url when no website is resolvable from context")
