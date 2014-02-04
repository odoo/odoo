import openerp.addons.website.tests.test_ui as test_ui

def load_tests(loader, base, _):
    base.addTest(test_ui.WebsiteUiSuite(test_ui.full_path(__file__,'event_test.js'), {'redirect': '/page/website.homepage'}, 60.0))
    return base
