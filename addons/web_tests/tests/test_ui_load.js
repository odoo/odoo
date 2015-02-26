// Load helper
var system = require('system');
phantom.injectJs(system.args[1]);
pt = new PhantomTest();
pt.run("/", "console.log('ok')", "console");
