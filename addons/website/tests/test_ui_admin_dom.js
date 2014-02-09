// Load helper
phantom.injectJs(phantom.args[0]);

pt = new PhantomTest();
pt.run_admin("/", "console.log('ok')", "window.openerp.website");

