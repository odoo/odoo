var options = JSON.parse(phantom.args);
var page = require('webpage').create();
var url = 'http://localhost:'+options.port;
page.open(url, function (status) {
    if (status !== 'success') {
        console.log('{ "event": "failure", "message": "'+url+' failed to load"}');
        phantom.exit();
    } else {
        page.evaluate(function() {
            $(document).on("tour:ready", function () {
                openerp.website.TestConsole.test('banner').run(true)
                console.log('{ "event": "success" }');
                phantom.exit();
            });
        });
    }
});