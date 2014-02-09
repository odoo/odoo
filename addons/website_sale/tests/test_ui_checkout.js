var testRunner = require('../../../website/tests/ui_suite/ui_test_runner.js');

testRunner.run_test('shop_buy_product', {
        "inject": [
            "./../../../website/static/src/js/website.tour.test.js",
            "./../../../website_sale/static/src/js/website.tour.sale.js"]
    });
