var options = JSON.parse(phantom.args);
var url = 'http://localhost:'+options.port;

var page = require('webpage').create();

page.onError = function(message, trace) {
    console.log('{ "event": "error", "message": "'+message+'"}');
};

function waitFor(ready, timeout) {
    var maxtimeOutMillis = timeout ? timeout*1000 : 10000;
    var start = new Date().getTime();
    var condition = ready();
    var interval = setInterval(function() {
        if ((new Date().getTime() - start < maxtimeOutMillis) && !condition ) {
            alert("TOTO")
            condition = ready();
        } else {
            if(!condition) {
                console.log('{ "event": "error", "message": "Timeout after'+maxtimeOutMillis+' ms" }');
                phantom.exit(1);
            } else {
                clearInterval(interval);
                console.log('{ "event": "success" }');
            }
        }
    }, 100);
};

page.open(url, function (status) {
    if (status !== 'success') {
        console.log('{ "event": "failure", "message": "'+url+' failed to load"}');
        phantom.exit(1);
    } else {
        waitFor(function () {
            return page.evaluate(function () {
                return window.openerp && window.openerp.website;
            });
        }, 5);
    }
});