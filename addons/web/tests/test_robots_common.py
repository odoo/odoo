from urllib.robotparser import RobotFileParser

from odoo.tests import HttpCase


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
            sections[useragent] = {'allow': [], 'disallow': []}
            for rule in entry.rulelines:
                if rule.allowance:
                    sections[useragent]['allow'].append(rule.path)
                else:
                    sections[useragent]['disallow'].append(rule.path)

    return sections


class RobotsTxtTestCommon(HttpCase):

    def assertRobotsTxtValues(self, expected_robots_config):
        """Helper to fetch robots.txt and assert exact expected configuration"""
        response = self.url_open('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'text/plain')

        actual_robots_config = parse_robots_txt(response.text)

        self.assertEqual(actual_robots_config, expected_robots_config)

        return response
