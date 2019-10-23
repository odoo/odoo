# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo.tests.common import BaseCase
from odoo.tools import topological_sort


def sample(population):
    return random.sample(
        population,
            random.randint(0, min(len(population), 5)))


class TestModulesLoading(BaseCase):
    def setUp(self):
        self.mods = [str(i) for i in range(1000)]

    def test_topological_sort(self):
        random.shuffle(self.mods)
        modules = [
            (k, sample(self.mods[:i]))
            for i, k in enumerate(self.mods)]
        random.shuffle(modules)
        ms = dict(modules)

        seen = set()
        sorted_modules = topological_sort(ms)
        for module in sorted_modules:
            deps = ms[module]
            self.assertGreaterEqual(
                seen, set(deps),
                        'Module %s (index %d), ' \
                        'missing dependencies %s from loaded modules %s' % (
                    module, sorted_modules.index(module), deps, seen
                ))
            seen.add(module)
