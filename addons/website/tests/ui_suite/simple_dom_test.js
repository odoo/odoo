var testRunner = require('./ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function simpleDomTest (page) {
    waitFor(function () {
        return page.evaluate(function () {
            return window.openerp && window.openerp.website
                && window.openerp.website.TestConsole;
        });
    }, function () {
        console.log('{ "event": "success" }');
        phantom.exit();
    }, 20000);
});