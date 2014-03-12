import openerp.addons.website.tests.test_ui as test_ui

def load_tests(loader, base, _):
    base.addTest(test_ui.WebsiteUiSuite(test_ui.full_path(__file__,'website_sale-add_product-test.js'),
        {'redirect': '/page/website.homepage'}))
    base.addTest(test_ui.WebsiteUiSuite(test_ui.full_path(__file__,'website_sale-sale_process-test.js'),
        {'redirect': '/page/website.homepage'}))
    base.addTest(test_ui.WebsiteUiSuite(test_ui.full_path(__file__,'website_sale-sale_process-test.js'),
        {'redirect': '/page/website.homepage', 'user': 'demo', 'password': 'demo'}))
    # Test has been commented in SAAS-3 ONLY, it must be activated in trunk. 
    # Log for test JS has been improved in trunk, so we stop to loss time in saas-3 and debug it directly in trunk.
    # Tech Saas & AL agreement
    # base.addTest(test_ui.WebsiteUiSuite(test_ui.full_path(__file__,'website_sale-sale_process-test.js'), {'path': '/', 'user': None}))
    return base