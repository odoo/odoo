from unittest.mock import patch
from urllib.robotparser import RobotFileParser

from odoo.tests import HttpCase, tagged


def parse_robots_txt(content):
    """
    Parse robots.txt content and extract allow/disallow rules per user agent.

    :param content: The raw string content of a robots.txt file.
    :type content: str

    :return: A dictionary where keys are user-agent strings and values are
            dictionaries with 'allow' and 'disallow' lists of paths.
            Example:
            {
                'Googlebot': {
                    'allow': ['/public'],
                    'disallow': ['/private']
                },
                '*': {
                    'allow': ['/open'],
                    'disallow': ['/admin']
                }
            }
    :rtype: dict
    """
    parser = RobotFileParser()

    lines = content.splitlines()
    parser.parse(lines)

    sections = {}

    all_entries = parser.entries[:]
    if parser.default_entry:
        all_entries.append(parser.default_entry)

    for entry in all_entries:
        for useragent in entry.useragents:
            sections.setdefault(useragent, {'allow': [], 'disallow': []})
            for rule in entry.rulelines:
                if rule.allowance:
                    sections[useragent]['allow'].append(rule.path)
                else:
                    sections[useragent]['disallow'].append(rule.path)

    return sections


class RobotsTxtTestCommon(HttpCase):

    def assertRobotsTxtValues(self, expected_robots_config):
        """Helper to fetch robots.txt and assert expected values are present"""
        response = self.url_open('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers['Content-Type'].startswith('text/plain'))

        actual_robots_config = parse_robots_txt(response.text)

        errors = []

        for user_agent, expected_rules in expected_robots_config.items():
            if user_agent not in actual_robots_config:
                errors.append(f"Expected user agent '{user_agent}' not found in robots.txt")
                continue

            actual_rules = actual_robots_config[user_agent]

            for expected_allow in expected_rules.get('allow', []):
                if expected_allow not in actual_rules['allow']:
                    errors.append(f"Expected allow rule '{expected_allow}' not found for user agent '{user_agent}'")

            for expected_disallow in expected_rules.get('disallow', []):
                if expected_disallow not in actual_rules['disallow']:
                    errors.append(f"Expected disallow rule '{expected_disallow}' not found for user agent '{user_agent}'")

        if errors:
            self.fail("Robots.txt validation failed:\n" + "\n".join(f"- {error}" for error in errors))

        return response

    def run_custom_directive_test(self, directive_data, expected_output):
        """Helper to test custom directives with given data"""
        with patch.object(self.registry['ir.http'], '_get_robots_directives', lambda self: directive_data):
            return self.assertRobotsTxtValues(expected_output)


@tagged('post_install', '-at_install')
class TestRobotsTxtExtensible(RobotsTxtTestCommon):

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
