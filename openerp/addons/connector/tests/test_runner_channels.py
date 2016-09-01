# -*- coding: utf-8 -*-
import doctest
from openerp.addons.connector.jobrunner import channels


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(channels))
    return tests
