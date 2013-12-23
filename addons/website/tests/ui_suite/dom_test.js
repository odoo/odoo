var options = JSON.parse(phantom.args);
var url = 'http://localhost:'+options.port+'/web#action=website.action_website&login=admin&password=admin';

var page = require('webpage').create();

page.onError = function(message, trace) {
    console.log('{ "event": "error", "message": "'+message+'"}');
    phantom.exit(1);
};

function waitFor(ready, callback, timeout) {
    var timeoutMillis = timeout ? Math.round(timeout*1000) : 10000;
    var start = new Date().getTime();
    var condition = ready();
    var interval = setInterval(function() {
        if ((new Date().getTime() - start < timeoutMillis) && !condition ) {
            condition = ready();
        } else {
            if(!condition) {
                console.log('{ "event": "error", "message": "Timeout after'+timeoutMillis+' ms" }');
                phantom.exit(1);
            } else {
                clearInterval(interval);
                callback();
            }
        }
    }, 100);
};

page.viewportSize = { width: 1920, height: 1080 };
page.open(url, function (status) {
    if (status !== 'success') {
        console.log('{ "event": "failure", "message": "'+url+' failed to load"}');
        phantom.exit(1);
    } else {
        waitFor(function () {
            return page.evaluate(function () {
                return window.openerp && window.openerp.website && window.openerp.website.TestConsole;
            });
        }, function () {
            console.log('{ "event": "success" }');
            phantom.exit();
        }, options.timeout);
    }
});