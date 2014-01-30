var testRunner = require('../../../website/tests/ui_suite/ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function blogTest (page, timeout) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.$ && window.openerp && window.openerp.website
                && window.openerp.website.Tour
                && window.openerp.website.Tour.get('blog');
        });
    }, function executeTest () {
        page.evaluate(function () {
            window.openerp.website.TestConsole.get('blog').run(true, true);
        });
    }, timeout/5);
});