from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.web.tests.test_robots import RobotsTxtTestCommon


@tagged('post_install', '-at_install')
class WebsiteRobotsTxtTestCommon(RobotsTxtTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.website = cls.env['website'].get_current_website()
        cls.website.domain = cls.base_url()


@tagged('post_install', '-at_install')
class TestWebsiteRobotsTxtExtensible(WebsiteRobotsTxtTestCommon):

    def test_robots_txt_empty_directives(self):
        """Test robots.txt with empty allow/disallow lists"""
        directive_data = {
            '*': {
                'allow': [],
                'disallow': [],
            }
        }

        expected_output = {}

        self.run_custom_directive_test(directive_data, expected_output)

    def test_robots_txt_with_multilingual_paths(self):
        """Test robots.txt includes language-prefixed paths"""
        lang_fr = self.env["res.lang"]._activate_lang("fr_FR")
        self.website.language_ids = [Command.link(lang_fr.id)]

        directive_data = {
            '*': {
                'allow': ['/shop'],
                'disallow': ['/admin'],
            }
        }

        expected_output = {
            '*': {
                'allow': ['/shop', '/fr/shop'],
                'disallow': ['/admin', '/fr/admin']
            }
        }

        self.run_custom_directive_test(directive_data, expected_output)

    def test_robots_txt_non_matching_domain(self):
        """Test robots.txt when URL doesn't match website domain"""
        self.website.domain = 'different-domain.com'

        directive_data = {
            '*': {
                'allow': ['/should-not-appear'],
                'disallow': ['/also-should-not-appear'],
            }
        }

        expected_output = {}
        self.run_custom_directive_test(directive_data, expected_output)
