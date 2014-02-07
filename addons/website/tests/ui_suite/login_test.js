var testRunner = require('./ui_test_runner.js');

testRunner.run_test('login_edit', {
        "inject": [
            "./../../../website/static/src/js/website.tour.test.js",
            "./../../../website/static/src/js/website.tour.test.admin.js"]
    });