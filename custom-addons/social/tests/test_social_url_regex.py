# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestUrlRegex(TransactionCase):
    def test_url_regex(self):
        url_www = self.env['social.post']._extract_url_from_message(
            "This is a message with a www.google.com URL to Google."
        )
        self.assertEqual(url_www, 'www.google.com', 'The Google URL should be extracted')

        url_https = self.env['social.post']._extract_url_from_message(
            "This is a message with a https://facebook.com URL to Facebook."
        )
        self.assertEqual(url_https, 'https://facebook.com', 'The Facebook URL should be extracted')

        url_https_www = self.env['social.post']._extract_url_from_message(
            "This is a message with a https://www.twitter.com URL to Twitter."
        )
        self.assertEqual(url_https_www, 'https://www.twitter.com', 'The Twitter URL should be extracted')

        no_url = self.env['social.post']._extract_url_from_message(
            "This is a message without any URL."
        )
        self.assertFalse(no_url, 'No URL should be extracted')
