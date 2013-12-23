var options = JSON.parse(phantom.args);
var url = 'http://localhost:'+options.port+'/web#action=website.action_website_homepage&login=admin&password=admin';

var page = require('webpage').create();

page.onError = function(message, trace) {
    console.log('{ "event": "error", "message": "'+message+'"}');
    phantom.exit(1);
};

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

page.viewportSize = { width: 1920, height: 1080 };
page.open(url, function (status) {
    if (status !== 'success') {
        console.log('{ "event": "failure", "message": "'+url+' failed to load"}');
        phantom.exit(1);
    } else {
        page.evaluate(function () {
            localStorage.clear();
        });
        waitFor(function () {
            return page.evaluate(function () {
                return window.openerp && window.openerp.website && window.openerp.website.TestConsole && window.openerp.website.TestConsole.test('banner');
            });
        }, function () {
            page.evaluate(function () {
                window.openerp.website.TestConsole.test('banner').run(true);
            });
            waitFor(function () {
                return page.evaluate(function () {
                    var $edit = $('button[data-action=edit]');
                    var $carousel = $('#wrap [data-snippet-id=carousel]');
                    var $columns = $('#wrap [data-snippet-id=three-columns]');
                    return $carousel && $carousel.length === 1
                        && $columns && $columns.length === 1
                        && $('button[data-action=edit]').is(":visible");
                });
            }, function () {
                console.log('{ "event": "success" }');
                phantom.exit();
            });
        });
    }
});