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
}

function run (test, onload, inject) {
    var options = JSON.parse(phantom.args);

    var timeout = options.timeout ? Math.round(parseFloat(options.timeout)*1000-5000) : 60000;

    var scheme = options.scheme ? options.scheme+'://' : 'http://';
    var host = options.host ? options.host : 'localhost';
    var port = options.port ? ':'+options.port : '';
    var path = options.path ? options.path : '/login';

    var queryParams = [];
    if (options.db) queryParams.push('db='+options.db);
    if (options.user) queryParams.push('login='+options.user);
    if (options.password) queryParams.push('key='+options.password);
    if (options.redirect) queryParams.push('redirect='+options.redirect);
    var query = queryParams.length > 0 ? '?'+queryParams.join('&') : '';

    var hashParams = [];
    if (options.action) hashParams.push('action='+options.action);
    var hash = hashParams.length > 0 ? '#'+hashParams.join('&') : '';

    var url = scheme+host+port+path+query+hash;

    var page = require('webpage').create();

    page.viewportSize = { width: 1440, height: 900 };

    page.onError = function(message, trace) {
        console.log('{ "event": "error", "message": "'+message+'"}');
        phantom.exit(1);
    };
    page.onAlert = function(message) {
        console.log(message);
        phantom.exit(1);
    };
    page.onConsoleMessage = function(message) {
        console.log(message);
        try {
            var result = JSON.parse(message);
            if (result.event === 'success') {
                phantom.exit(0);
            } else if (result.event === 'console') {
                return;
            } else {
                phantom.exit(1);
            }
        } catch (exception) {
            phantom.exit(1);
        }
    };

    page.onCallback = function(data) {
        if (data.event && data.event === 'start') {
            if (test) test(page, timeout, options);
        }
    };
    page.onLoadFinished = function(status) {
        if (status === "success") {
            if (inject) {
                if (!inject instanceof Array) {
                    inject = [inject];
                }
                for (var k in inject) {
                    if(!page.injectJs(inject[k])) {
                        console.log("Can't inject "+inject[k]);
                        phantom.exit(1);
                    }
                }
            }
            if (onload) onload(page, timeout, options);
        }
    };
    
    var maxRetries = 10;
    var retryDelay = 1000; // ms
    var tries = 0;
    page.open(url, function openPage (status) {
        if (status !== 'success') {
            tries++;
            if (tries < maxRetries) {
                setTimeout(function () {
                    page.open(url, openPage);
                }, retryDelay);
            } else {
                console.log('{ "event": "error", "message": "'+url+' failed to load '+tries+' times ('+status+')"}');
                phantom.exit(1);
            }
        } else {
            page.evaluate(function () {
                window.callPhantom({ event: 'start' });
            });
        }

    });

    setTimeout(function () {
        page.evaluate(function (timeout) {
            var message = ("Timeout after " +(timeout/1000)+ " s"
                + "\nhref: " + window.location.href
                + "\nreferrer: " + document.referrer
                + "\n\n" + document.body.innerHTML).replace(/[^a-z0-9\s~!@#$%^&*()_|+\-=?;:'",.<>\{\}\[\]\\\/]/gi, "*");
            console.log(JSON.stringify({ "event": "error", "message": message}));
            phantom.exit(1);
        },timeout);
    }, timeout);
}

function run_test (testname, options) {
    options = options || {};
    run(
        function start (page, timeout) {
            page.evaluate(function () { localStorage.clear(); });
        },
        function onload (page, timeout) {
            waitFor(function clientReady () {
                return page.evaluate(function () {
                    return window.$
                        && window.openerp
                        && window.openerp.website
                        && window.openerp.website.Tour;
                });
            }, function executeTest () {
                page.evaluate(function (testname) {
                    window.openerp.website.Tour.run_test(testname);
                }, testname);
            }, timeout);
        },
        options.inject || null
    );
}

module.exports = {
    waitFor: waitFor,
    run: run,
    run_test: run_test
}
