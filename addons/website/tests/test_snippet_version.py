# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged
from unittest.mock import patch
from lxml import etree, html
from collections import defaultdict


@tagged('post_install', '-at_install')
class TestSnippetVersion(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Website = self.env['website']

    def test_snippet_version(self):
        current_snippet_versions = self._get_snippet_version_in_template()
        all_mismatches = self._check_used_snippet_version(current_snippet_versions)

        self.assertEqual(all_mismatches, [])

    def test_data_snippet_attribute(self):
        missing_data_snippet = []
        html_fields = [(self.env[model_name], field_name) for model_name, field_name in self.Website._get_html_fields()]
        for model, field_name in html_fields:
            records = model.search([(field_name, '!=', False)])
            for record in records:
                html_content = record[field_name]
                tree = html.fromstring(html_content.encode('utf-8'))
                for element in tree.xpath('//*[@data-vxml or @data-vcss or @data-vjs][preceding::*[@class]]'):
                    if 'data-snippet' not in element.attrib:
                        missing_data_snippet.append((record, element.attrib))

        self.assertEqual(missing_data_snippet, [])

    def _get_snippet_version_in_template(self):
        snippet_versions = {}
        snippet_templates = self.env['ir.ui.view'].search([
            ('key', 'like', 'website%.s\\_'),
            '!', ('key', 'like', 'mail%.s\\_'),
            '!', ('key', '=like', '%\\_options'),
            ('type', '=', 'qweb')
        ])
        for template in snippet_templates:
            snippet_id = template["key"].split(".")[1]
            tree = etree.fromstring(template["arch_db"].encode('utf-8'))
            for element in tree.xpath('//*[@data-vxml or @data-vcss or @data-vjs]'):
                if element.attrib.get('data-snippet', snippet_id) == snippet_id:
                    snippet_versions[snippet_id] = {
                        'data-vxml': element.attrib.get('data-vxml', '000'),
                        'data-vcss': element.attrib.get('data-vcss', '000'),
                        'data-vjs': element.attrib.get('data-vjs', '000'),
                    }
            if snippet_id not in snippet_versions:
                snippet_versions[snippet_id] = {
                    'data-vxml': '000',
                    'data-vcss': '000',
                    'data-vjs': '000'
                }
        return snippet_versions

    def _check_used_snippet_version(self, snippet_versions):

        all_mismatches = []
        known_mismatches = ['website_hr_recruitment.default_website_description']
        html_fields = [(self.env[model_name], field_name) for model_name, field_name in self.Website._get_html_fields()]
        for model, field_name in html_fields:
            records = model.search([(field_name, '!=', False)])
            for record in records:
                key = str(record["key"]) if "key" in record else f"{model._name}.{field_name}"
                if key in known_mismatches or 'marketing' in key.split(".")[0] or 'mail' in key.split(".")[0]:
                    continue
                html_content = record[field_name]
                tree = html.fromstring(html_content.encode('utf-8'))
                for element in tree.xpath('//*[@data-snippet]'):
                    snippet_id = element.attrib.get('data-snippet')
                    versions = {
                        'data-vxml': element.attrib.get('data-vxml', '000'),
                        'data-vcss': element.attrib.get('data-vcss', '000'),
                        'data-vjs': element.attrib.get('data-vjs', '000'),
                    }
                    if snippet_id not in snippet_versions:
                        all_mismatches.append((key, snippet_id, 'Unknown snippet'))
                        continue
                    official_versions = snippet_versions[snippet_id]
                    mismatches = {k: (v, official_versions.get(k)) for k, v in versions.items() if v != official_versions.get(k)}
                    if mismatches:
                        all_mismatches.append((key, snippet_id, mismatches))
        return all_mismatches
