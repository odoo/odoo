var options = JSON.parse(phantom.args);
var url = 'http://localhost:'+options.port+'/web#action=website.action_website&login=admin&password=admin';

var page = require('webpage').create();

page.onError = function(message, trace) {
    console.log('{ "event": "error", "message": "'+message+'"}');
};

function waitFor(ready, timeout) {
    var timeOutMillis = timeout ? timeout*1000 : 10000;
    var start = new Date().getTime();
    var condition = ready();
    var interval = setInterval(function() {
        if ((new Date().getTime() - start < timeOutMillis) && !condition ) {
            condition = ready();
        } else {
            if(!condition) {
                console.log('{ "event": "error", "message": "Timeout after'+timeOutMillis+' ms" }');
                phantom.exit(1);
            } else {
                clearInterval(interval);
                console.log('{ "event": "success" }');
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
        }, options.timeout);
    }
});