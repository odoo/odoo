from urllib.parse import quote

from odoo.tests import HttpCase, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteSettingsTour(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website_1 = cls.env['website'].search([], limit=1)
        cls.website_1.name = "Website 1"

        cls.website_2 = cls.env['website'].create({
            'name': "Website 2",
            'company_id': cls.env.company.id,
        })

    def test_settings_active_website_preselected(self):
        preview_path = self.website_2.get_client_action_url("/")

        tour_url = f"/website/force/{self.website_2.id}?path={quote(preview_path)}"

        self.start_tour(
            tour_url,
            "website_settings_preselect_tour",
            login="admin",
        )


@tagged('post_install', '-at_install')
class TestWebsiteSettingsMultiCompany(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_1 = cls.env.company
        cls.company_2 = cls.env['res.company'].create({'name': 'Company 2'})

        # Fetch the default website safely
        cls.website_1 = cls.env['website'].search([], limit=1)
        cls.website_1.company_id = cls.company_1.id

        cls.website_2 = cls.env['website'].create({
            'name': 'Website 2',
            'company_id': cls.company_2.id,
        })

        # User restricted to Company 1
        cls.user_company_1 = cls.env['res.users'].create({
            'name': 'Manager Company 1',
            'login': 'manager_c1',
            'company_id': cls.company_1.id,
            'company_ids': [(6, 0, [cls.company_1.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_system').id,
                cls.env.ref('website.group_website_designer').id,
            ])],
        })

    def test_default_website_with_host_id_cross_company(self):
        """ Ensure a target website is preselected via host_id even if it belongs
        to a company the user is not actively in. The website model is globally
        readable, allowing cross-company review (saves are blocked by ir.rule). """

        env_c2 = self.env['res.config.settings'].with_user(self.user_company_1).with_context(
            host_id=self.website_2.id,
        )

        values = env_c2.default_get(['website_id'])
        self.assertEqual(
            values.get('website_id'),
            self.website_2.id,
            "Website 2 should be preselected based on host_id, even across companies.",
        )

    def test_default_website_id_precedence_over_host_id(self):
        """ Ensure the explicit caller parameter 'default_website_id' always
        takes precedence over the implicit request-level 'host_id'. """

        env_explicit = self.env['res.config.settings'].with_context(
            default_website_id=self.website_1.id,
            host_id=self.website_2.id,
        )

        values = env_explicit.default_get(['website_id'])

        self.assertEqual(
            values.get('website_id'),
            self.website_1.id,
            "An explicit default_website_id must bypass the host_id evaluation.",
        )
