from unittest.mock import patch

from odoo.addons.web.tests.test_robots_common import RobotsTxtTestCommon
from odoo.fields import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class WebsiteRobotsTxtTestCommon(RobotsTxtTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.website = cls.env['website'].get_current_website()
        cls.website.domain = cls.base_url()


@tagged('post_install', '-at_install')
class TestRobotsTxtExtensible(WebsiteRobotsTxtTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def run_custom_directive_test(self, directive_data, expected_output):
        """Helper to test custom directives with given data"""
        with patch.object(self.registry['ir.http'], '_get_robots_directives', lambda self: directive_data):
            return self.assertRobotsTxtValues(expected_output)

    def test_robots_txt_default_behavior(self):
        """Test default robots.txt behavior using _get_allowed_robots_routes"""
        with patch.object(self.registry['ir.http'], '_get_allowed_robots_routes', lambda self: ['/shop', '/blog']):
            self.assertRobotsTxtValues({
                '*': {
                    'allow': ['/shop', '/blog'],
                    'disallow': []
                }
            })

    def test_robots_txt_custom_directives_single_agent(self):
        """Test robots.txt with custom directives for single user agent"""
        directive_data = {
            '*': {
                'allow': ['/public', '/products'],
                'disallow': ['/private', '/admin'],
            }
        }

        expected_output = {
            '*': {
                'allow': ['/public', '/products'],
                'disallow': ['/private', '/admin'],
            }
        }

        self.run_custom_directive_test(directive_data, expected_output)

    def test_robots_txt_custom_directives_multiple_agents(self):
        """Test robots.txt with custom directives for multiple user agents"""
        directive_data = {
            'Googlebot': {
                'allow': ['/google-content'],
                'disallow': ['/no-google'],
            },
            'Bingbot': {
                'allow': ['/bing-content'],
                'disallow': ['/no-bing'],
            },
            '*': {
                'allow': ['/general'],
                'disallow': ['/restricted'],
            }
        }

        expected_output = {
            'Googlebot': {
                'allow': ['/google-content'],
                'disallow': ['/no-google'],
            },
            'Bingbot': {
                'allow': ['/bing-content'],
                'disallow': ['/no-bing'],
            },
            '*': {
                'allow': ['/general'],
                'disallow': ['/restricted'],
            },
        }

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

    def test_robots_txt_disabled_by_config(self):
        """Test robots.txt when disabled by configuration"""
        self.env['ir.config_parameter'].sudo().set_param('website.disable_robots_optimization', True)

        directive_data = {
            '*': {
                'allow': ['/should-not-appear'],
                'disallow': ['/also-should-not-appear'],
            }
        }

        expected_output = {}

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
