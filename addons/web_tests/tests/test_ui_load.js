// Load helper
phantom.injectJs(phantom.args[0]);
pt = new PhantomTest();
pt.run("/", "console.log('ok')", "console");
