var testRunner = require('./ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function homepageTest (page, timeout) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.$ && window.openerp && window.openerp.website
                && window.openerp.website.Tour
                && window.openerp.website.Tour.get('banner');
        });
    }, function executeTest () {
        var before = page.evaluate(function () {
            var result = {
                carousel: $('#wrap [data-snippet-id=carousel]').length,
                columns: $('#wrap [data-snippet-id=three-columns]').length,
            };
            window.openerp.website.Tour.get('banner').run(true, true);
            return result;
        });
        waitFor(function testExecuted () {
            var after = page.evaluate(function () {
                return window.$ && $('button[data-action=edit]').is(":visible") && {
                    carousel: $('#wrap [data-snippet-id=carousel]').length,
                    columns: $('#wrap [data-snippet-id=three-columns]').length,
                };
            });
            return after && (after.carousel === before.carousel + 1) && (after.columns === before.columns + 1);
        }, function finish () {
            console.log('{ "event": "success" }');
            phantom.exit();
        }, 4*timeout/5);
    }, timeout/5);
});
