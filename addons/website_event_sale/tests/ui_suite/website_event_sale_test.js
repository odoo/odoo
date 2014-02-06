var testRunner = require('../../../website/tests/ui_suite/ui_test_runner.js');

testRunner.run_test('event_buy_tickets', {
        "inject": [
            "./../../../website/static/src/js/website.tour.test.js",
            "./../../../website_event_sale/static/src/js/website.tour.event_sale.js"]
    });