var testRunner = require('../../../website/tests/ui_suite/ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function websiteSaleTest (page, timeout) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.$ && window.openerp && window.openerp.website
                && window.openerp.website.Tour
                && window.openerp.website.Tour.get('shop');
        });
    }, function executeTest () {
        page.evaluate(function () {
            window.openerp.website.Tour.get('shop').run(true, true);
        });
        waitFor(function testExecuted () {
            var after = page.evaluate(function () {
                return window.$ && $('button[data-action=edit]').is(":visible") &&
                    $('data-snippet-id="big-picture"').length;
            });
            return after;
        }, function finish () {
            console.log('{ "event": "success" }');
            phantom.exit();
        }, 4*timeout/5);
    }, timeout/5);
});
