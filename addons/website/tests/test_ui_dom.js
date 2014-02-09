var testRunner = require('./ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function simpleDomTest (page, timeout) {
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.openerp && window.openerp.website;
        });
    }, function finish () {
        console.log('{ "event": "success" }');
        phantom.exit();
    }, timeout);
});