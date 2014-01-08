var testRunner = require('../../../website/tests/ui_suite/ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function homepageTest (page, timeout) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function clientReady () {
        return page.evaluate(function () {
            return window.$ && window.openerp && window.openerp.website
                && window.openerp.website.TestConsole
                && window.openerp.website.TestConsole.test('blog');
        });
    }, function executeTest () {
        page.evaluate(function () {
            window.openerp.website.TestConsole.test('blog').run(true);
        });
        waitFor(function testExecuted () {
            var after = page.evaluate(function () {
                return window.$ && $('button[data-action=edit]').is(":visible") && {
                    image: $('#wrap [data-snippet-id=image-text]').length,
                    text: $('#wrap [data-snippet-id=text-block]').length,
                };
            });
            var result = after && (after.image === 1) && (after.text === 1);
            if (!result && window.location.href.indexOf('/blogpost/') > 0) {
                window.location.reload();
            }
            return result;
        }, function finish () {
            console.log('{ "event": "success" }');
            phantom.exit();
        }, 4*timeout/5);
    }, timeout/5);
});