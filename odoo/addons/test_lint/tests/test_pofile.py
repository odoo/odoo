# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
import logging
import tempfile

from odoo.modules import get_modules, get_resource_path
from odoo.tests.common import TransactionCase
from odoo.tools.translate import TranslationFileReader, trans_export, duplicate_key
from odoo.tests import tagged

_logger = logging.getLogger(__name__)


class PotLinter(TransactionCase):
    def test_pot_duplicate_entries(self):
        # retrieve all modules, and their corresponding POT file
        for module in get_modules():
            filename = get_resource_path(module, 'i18n', module + '.pot')
            if not filename:
                continue
            counts = Counter(map(duplicate_key, TranslationFileReader(filename)))
            duplicates = [key for key, count in counts.items() if count > 1]
            self.assertFalse(duplicates, "Duplicate entries found in %s" % filename)


@tagged('-at_install', 'post_install')
class TestMissingPot(TransactionCase):
    def test_pot_missing_entries(self):
        suggest_update = False
        for module in sorted(get_modules()):
            if module.startswith('l10n_') or module.startswith('test_'):
                continue
            with self.subTest(module=module):
                filename = get_resource_path(module, 'i18n', module + '.pot')
                current = set(map(duplicate_key, TranslationFileReader(filename))) if filename else set()
                with tempfile.NamedTemporaryFile(mode='wb') as buf:
                    trans_export(False, [module], buf, 'po', self.cr)
                    expected = set(map(duplicate_key, TranslationFileReader(buf.name)))

                try:
                    self.assertTrue(filename or not expected)
                    self.assertFalse(expected - current)
                except AssertionError:
                    suggest_update = True
                    raise

        if suggest_update:
            _logger.warning(
                "HINT: use this script to update the translations templates: "
                "https://gist.github.com/william-andre/01a5ff34f9bfc1f407eb162ed8b53a5f"
            )
