function waitFor (ready, callback, timeout, timeoutMessageCallback) {
    timeout = timeout || 10000;
    var start = new Date().getTime();
    var condition = ready();
    var interval = setInterval(function() {
        if ((new Date().getTime() - start < timeout) && !condition ) {
            condition = ready();
        } else {
            if(!condition) {
                var message = timeoutMessageCallback ? timeoutMessageCallback() : "Timeout after "+timeout+" ms";
                console.log('{ "event": "error", "message": "'+message+'" }');
                console.log("Waiting for...\n"+ready);
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
    var scheme = options.scheme ? options.scheme+'://' : 'http://';
    var host = options.host ? options.host : 'localhost';
    var port = options.port ? ':'+options.port : '';
    var path = options.path ? options.path : '/web';

    var queryParams = [];
    if (options.db) queryParams.push('db='+options.db);
    var query = queryParams.length > 0 ? '?'+queryParams.join('&') : '';

    var hashParams = [];
    if (options.user) hashParams.push('login='+options.user);
    if (options.admin_password) hashParams.push('password='+options.admin_password);
    if (options.action) hashParams.push('action='+options.action);
    var hash = hashParams.length > 0 ? '#'+hashParams.join('&') : '';

    var url = scheme+host+port+path+query+hash;
    var page = require('webpage').create();
    page.viewportSize = { width: 1920, height: 1080 };
    page.onError = function(message, trace) {
        console.log('{ "event": "error", "message": "'+message+'"}');
        phantom.exit(1);
    };
    page.open(url, function (status) {
        if (status !== 'success') {
            console.log('{ "event": "error", "message": "'+url+' failed to load"}');
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