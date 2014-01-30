import openerp
import openerp.addons.website.tests.test_ui as test_ui

def load_tests(loader, base, _):
    jsfile = openerp.modules.module.get_module_resource('website_sale','tests','test_sale_process1.js')
    base.addTest(test_ui.WebsiteUiSuite(jsfile,{ 'action': 'website.action_website_homepage' }, 120.0))
    jsfile = openerp.modules.module.get_module_resource('website_sale','tests','test_sale_process2.js')
    base.addTest(test_ui.WebsiteUiSuite(jsfile,{ 'action': 'website.action_website_homepage' }, 120.0))
    return base
