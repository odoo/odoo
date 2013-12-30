var testRunner = require('./ui_test_runner.js');

var waitFor = testRunner.waitFor;

testRunner.run(function simpleDomTest (page) {
    waitFor(function openerpFrameworkReady () {
        return page.evaluate(function () {
            return window.openerp && window.openerp.website;
        });
    }, function success () {
        console.log('{ "event": "success" }');
        phantom.exit();
    }, 20000, function errorStatus () {
        var status = page.evaluate(function () {
            return {
                href: window.location.href,
                jQueryFound: (typeof window.$ === 'function'),
                openerpFound: (typeof window.openerp === 'object')
            }
        });
        return status.href+" with jQuery ("+status.jQueryFound+") and openerp (" +status.openerpFound+ ")";
    });
});