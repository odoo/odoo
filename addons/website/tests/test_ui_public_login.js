// Load helper
phantom.injectJs(phantom.args[0]);

pt = new PhantomTest();
pt.inject = [
    "./../../../website/static/src/js/website.tour.test.js",
    "./../../../website/static/src/js/website.tour.test.admin.js"]
];
pt.run("/", "openerp.website.Tour.run_test('login_edit')", "openerp.website.Tour");

