import os

import openerp.addons.website.tests.test_ui as test_ui

def full_path(filename):
    return os.path.join(os.path.join(os.path.dirname(__file__), 'ui_suite'), filename)

def load_tests(loader, base, _):
    base.addTest(test_ui.WebsiteUiSuite(full_path('event_test.js'), {'redirect': '/page/website.homepage'}, 60.0))
    return base
