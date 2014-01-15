var testRunner = require('../../../website/tests/ui_suite/ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function eventTest (page, timeout) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.$ && window.openerp && window.openerp.website
                && window.openerp.website.TestConsole
                && window.openerp.website.TestConsole.test('event');
        });
    }, function executeTest () {
        page.evaluate(function () {
            window.openerp.website.TestConsole.test('event').run(true);
        });
        waitFor(function testExecuted () {
            var after = page.evaluate(function () {
                return window.$ && $('button[data-action=edit]').is(":visible") && {
                    banner: $('#wrap [data-snippet-id=carousel]').length,
                    text: $('#wrap [data-snippet-id=text-block]').length,
                    image: $('#wrap [data-snippet-id=three-columns]').length,
                };
            });
            var result = after && (after.banner === 1) && (after.text === 1) && (after.image === 1);
            return result;
        }, function finish () {
            console.log('{ "event": "success" }');
            phantom.exit();
        }, 4*timeout/5);
    }, timeout/5);
});