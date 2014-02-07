var testRunner = require('./ui_test_runner.js');

testRunner.run(
        function onload (page, timeout, options) {
            page.evaluate(function (user, password) {
                window.password = password;
                window.user = user;
            }, options.user, options.password);
        },
        [   "./../../../website/static/src/js/website.tour.test.js",
            "./../../../website/static/src/js/website.tour.test.admin.js"]
    );