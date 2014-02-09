// Load helper
phantom.injectJs(phantom.args[0]);

pt = new PhantomTest();
pt.run_admin("/", "openerp.website.Tour.run_test('banner')", "openerp.website.Tour");

