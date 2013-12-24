function waitFor(ready, callback, timeout) {
    var timeoutMillis = timeout ? Math.round(timeout*1000) : 30000;
    var start = new Date().getTime();
    var condition = ready();
    var interval = setInterval(function() {
        if ((new Date().getTime() - start < timeoutMillis) && !condition ) {
            condition = ready();
        } else {
            if(!condition) {
                console.log('{ "event": "error", "message": "Timeout after '+timeoutMillis+' ms" }');
                phantom.exit(1);
            } else {
                clearInterval(interval);
                callback();
            }
        }
    }, 100);
};

function run (test) {
    var options = JSON.parse(phantom.args);
    var port = options.port ? ':'+options.port : '';
    var path = options.path ? options.path : '';
    var url = 'http://localhost'+port+path;
    var page = require('webpage').create();
    page.viewportSize = { width: 1920, height: 1080 };
    page.onError = function(message, trace) {
        console.log('{ "event": "error", "message": "'+message+'"}');
        phantom.exit(1);
    };
    page.open(url, function (status) {
        if (status !== 'success') {
            console.log('{ "event": "failure", "message": "'+url+' failed to load"}');
            phantom.exit(1);
        } else {
            test(page);
        }
    });
}

module.exports = {
    waitFor: waitFor,
    run: run
}