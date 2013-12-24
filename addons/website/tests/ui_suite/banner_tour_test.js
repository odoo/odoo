var testRunner = require('./ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function testBannerTour (page) {
    page.evaluate(function () { localStorage.clear(); });
    waitFor(function () {
        return page.evaluate(function () {
            return window.openerp && window.openerp.website
                && window.openerp.website.TestConsole
                && window.openerp.website.TestConsole.test('banner');
        });
    }, function () {
        page.evaluate(function () {
            window.openerp.website.TestConsole.test('banner').run(true);
        });
        waitFor(function () {
            return page.evaluate(function () {
                var $edit = $('button[data-action=edit]');
                var $carousel = $('#wrap [data-snippet-id=carousel]');
                var $columns = $('#wrap [data-snippet-id=three-columns]');
                return $carousel.length === 1 && $columns.length === 1
                    && $('button[data-action=edit]').is(":visible");
            });
        }, function () {
            console.log('{ "event": "success" }');
            phantom.exit();
        });
    });
});