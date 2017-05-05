# -*- coding: utf-8 -*-
import doctest
from openerp.addons.connector.jobrunner import runner


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(runner))
    return tests
