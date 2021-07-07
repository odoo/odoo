# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from lxml import etree
import re

from odoo.addons.website.tools import distance
import odoo.tests
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

@odoo.tests.tagged('-at_install', 'post_install')
class TestFuzzy(TransactionCase):
    def test_01_fuzzy_names(self):
        # Models from other modules commented out on commit: they make the test much longer
        # Last results observed across modules:
        # - 698 words in target dictionary
        # - 21 wrong guesses over 9379 tested typos (0.22%)
        # - Duration: ~5.7 seconds
        fields_per_model = {
            'website.page': ['name', 'arch'],
            # 'product.public.category': ['name', 'website_description'],
            # 'product.template': ['name', 'description_sale'],
            # 'blog.blog': ['name', 'subtitle'],
            # 'blog.post': ['name', 'subtitle'],
            # 'slide.channel': ['name', 'description_short'],
            # 'slide.slide': ['name', 'description'],
            # 'event.event': ['name', 'subtitle'],
        }
        match_pattern = '\\w{4,}'
        words = set()
        for model_name, fields in fields_per_model.items():
            if model_name not in self.env:
                continue
            model = self.env[model_name]
            if 'description' not in fields and 'description' in model:
                fields.append('description') # larger target dataset
            records = model.sudo().search_read([], fields, limit=100)
            for record in records:
                for field, value in record.items():
                    if isinstance(value, str):
                        if field == 'arch':
                            view_arch = etree.fromstring(value.encode('utf-8'))
                            value = ' '.join(view_arch.itertext())
                        for word in re.findall(match_pattern, value):
                            words.add(word.lower())
        _logger.info("%s words in target dictionary", len(words))

        website = self.env.ref('website.default_website')

        typos = {}
        def add_typo(expected, typo):
            if typo not in words:
                typos.setdefault(typo, set()).add(expected)

        for search in words:
            for index in range(2, len(search)):
                # swap letters
                if search[index] != search[index - 1]:
                    add_typo(search, search[:index - 1] + search[index] + search[index - 1] + search[index + 1:])
                # miss letter
                if len(search) > 4:
                    add_typo(search, search[:index - 1] + search[index:])
                # wrong letter
                add_typo(search, search[:index - 1] + '!' + search[index:])

        words = list(words)
        words.sort() # guarantee results stability
        mismatch_count = 0
        for search, expected in typos.items():
            fuzzy_guess = website._search_find_fuzzy_term({}, search, word_list=words)
            if not fuzzy_guess or (fuzzy_guess not in expected and fuzzy_guess not in [exp[:-1] for exp in expected]):
                mismatch_count += 1
                _logger.info("'%s' fuzzy matched to '%s' instead of %s", search, fuzzy_guess, expected)

        ratio = 100.0 * mismatch_count / len(typos)
        _logger.info("%s wrong guesses over %s tested typos (%.2f%%)", mismatch_count, len(typos), ratio)
        typos.clear()
        words.clear()
        self.assertTrue(ratio < 1, "Too many wrong fuzzy guesses")

    def test_02_distance(self):
        self.assertEqual(distance("gravity", "granity", 3), 1)
        self.assertEqual(distance("gravity", "graity", 3), 1)
        self.assertEqual(distance("gravity", "grait", 3), 2)
        self.assertEqual(distance("gravity", "griaty", 3), 3)
        self.assertEqual(distance("gravity", "giraty", 3), 3)
        self.assertEqual(distance("gravity", "giraty", 2), -1)
        self.assertEqual(distance("gravity", "girafe", 3), -1)
        self.assertEqual(distance("warranty", "warantl", 3), 2)

        # non-optimized cases still have to return correct results
        self.assertEqual(distance("warranty", "warranty", 3), 0)
        self.assertEqual(distance("", "warranty", 3), -1)
        self.assertEqual(distance("", "warranty", 10), 8)
        self.assertEqual(distance("warranty", "", 10), 8)
        self.assertEqual(distance("", "", 10), 0)
