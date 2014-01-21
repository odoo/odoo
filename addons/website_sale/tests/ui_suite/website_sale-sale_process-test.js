var testRunner = require('../../../website/tests/ui_suite/ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function websiteSaleTest (page, timeout) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.$ && window.openerp && window.openerp.website
                && window.openerp.website.TestConsole
                && window.openerp.website.TestConsole.test('shoptest');
        });
    }, function executeTest () {
        page.evaluate(function () {
            window.openerp.website.TestConsole.test('shoptest').run(true);
        });
        waitFor(function testExecuted () {
            return page.evaluate(function () {
                var res = window.localStorage && window.localStorage.getItem
                    && window.localStorage.getItem("test-success");
            console.log('{ "error": "testExecuted", "message": "'+res+'"" }');
                return res;
            });
        }, function finish () {
            console.log('{ "event": "success" }');
            phantom.exit();
        }, 4*timeout/5);
    }, timeout/5);
});