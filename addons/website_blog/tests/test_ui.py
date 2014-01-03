import os

import openerp.addons.website.tests.test_ui as test_ui

def full_path(filename):
    return os.path.join(os.path.join(os.path.dirname(__file__), 'ui_suite'), filename)

def load_tests(loader, base, _):
    base.addTest(test_ui.WebsiteUiSuite(full_path('post_test.js'),   { 'action': 'website.action_website_homepage' }, 120.0))
    return base