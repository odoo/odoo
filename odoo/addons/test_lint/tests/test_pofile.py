# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter

from odoo.tools.translate import translation_file_reader

from .common import LintCase


class PotLinter(LintCase):
    def test_pot_duplicate_entries(self):
        def format(entry):
            # translation_file_reader only returns those three types
            if entry['type'] == 'model':
                return ('model', entry['name'], entry['imd_name'])
            elif entry['type'] == 'model_terms':
                return ('model_terms', entry['name'], entry['imd_name'], entry['src'])
            elif entry['type'] == 'code':
                return ('code', entry['src'])

        # retrieve all modules, and their corresponding POT file
        for filename in self.iter_module_files('*/i18n/*.pot'):
            counts = Counter(map(format, translation_file_reader(filename)))
            duplicates = [key for key, count in counts.items() if count > 1]
            self.assertFalse(duplicates, "Duplicate entries found in %s" % filename)
