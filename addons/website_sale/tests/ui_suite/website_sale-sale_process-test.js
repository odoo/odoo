var testRunner = require('../../../website/tests/ui_suite/ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function websiteSaleTest (page, timeout) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.$ && window.openerp && window.openerp.website
                && window.openerp.website.Tour;
        });
    }, function executeTest () {
        page.evaluate(function () {
            window.openerp.website.Tour.run_test('shop_buy_product');
        });
    }, timeout);
});