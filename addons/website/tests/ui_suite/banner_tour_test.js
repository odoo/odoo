var testRunner = require('./ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function testBannerTour (page) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.openerp && window.openerp.website
                && window.openerp.website.TestConsole
                && window.openerp.website.TestConsole.test('banner');
        });
    }, function executeTest () {
        var before = page.evaluate(function () {
            var result = {
                carousel: $('#wrap [data-snippet-id=carousel]').length,
                columns: $('#wrap [data-snippet-id=three-columns]').length,
            };
            window.openerp.website.TestConsole.test('banner').run(true);
            return result;
        });
        waitFor(function testExecuted () {
            var after = page.evaluate(function () {
                if ($('button[data-action=edit]').is(":visible")) {
                    return {
                        carousel: $('#wrap [data-snippet-id=carousel]').length,
                        columns: $('#wrap [data-snippet-id=three-columns]').length,
                    };
                }
            });
            return after && after.carousel === before.carousel + 1 && after.columns === before.columns + 1;
        }, function finish () {
            console.log('{ "event": "success" }');
            phantom.exit();
        }, 30000);
    }, 20000);
});