var testRunner = require('../../../website/tests/ui_suite/ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function websiteSaleTest (page, timeout) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.$ && window.openerp && window.openerp.website
                && window.openerp.website.Tour
                && window.openerp.website.Tour.get('shop_buy_product');
        });
    }, function executeTest () {
        page.evaluate(function () {
            window.openerp.website.TestConsole.get('shop_buy_product').run(true, true);
        });
    }, timeout);
});