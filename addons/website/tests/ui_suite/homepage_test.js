var testRunner = require('./ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function homepageTest (page, timeout) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.$ && window.openerp && window.openerp.website
                && window.openerp.website.Tour;
        });
    }, function executeTest () {
        page.evaluate(function () {
            window.openerp.website.Tour.run_test('banner');
        });
    }, timeout);
});
