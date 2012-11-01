# -*- coding: utf-8 -*-

import random
import unittest2

from ..controllers.main import module_topological_sort as sort

def sample(population):
    return random.sample(
        population,
            random.randint(0, min(len(population), 5)))

class TestModulesLoading(unittest2.TestCase):
    def setUp(self):
        self.mods = map(str, range(1000))
    def test_topological_sort(self):
        random.shuffle(self.mods)
        modules = [
            (k, sample(self.mods[:i]))
            for i, k in enumerate(self.mods)]
        random.shuffle(modules)
        ms = dict(modules)

        seen = set()
        sorted_modules = sort(ms)
        for module in sorted_modules:
            deps = ms[module]
            self.assertGreaterEqual(
                seen, set(deps),
                        'Module %s (index %d), ' \
                        'missing dependencies %s from loaded modules %s' % (
                    module, sorted_modules.index(module), deps, seen
                ))
            seen.add(module)
