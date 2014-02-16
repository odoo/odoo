// Phantomjs openerp helper

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
                console.log(message);
                console.log("Waiting for " + ready);
                console.log("error");
                phantom.exit(1);
            } else {
                clearInterval(interval);
                callback();
            }
        }
    }, 250);
}

function PhantomTest() {
    var self = this;
    this.options = JSON.parse(phantom.args[phantom.args.length-1]);
    this.inject = [];
    this.timeout = this.options.timeout ? Math.round(parseFloat(this.options.timeout)*1000 - 5000) : 10000;
    this.origin = 'http://localhost';
    this.origin += this.options.port ? ':' + this.options.port : '';

    // ----------------------------------------------------
    // test reporting
    // ----------------------------------------------------
    this.error = function(message) {
        console.log(message);
        console.log("error");
        phantom.exit(1);
    };

    // ----------------------------------------------------
    // configure phantom and page
    // ----------------------------------------------------
    phantom.addCookie({
        'domain': 'localhost',
        'name': 'session_id',
        'value': this.options.session_id,
    });
    this.page = require('webpage').create();
    this.page.viewportSize = { width: 1366, height: 768 };
    this.page.onError = function(message, trace) {
        self.error(message + " " + trace);
    };
    this.page.onAlert = function(message) {
        self.error(message);
    };
    this.page.onConsoleMessage = function(message) {
        console.log(message);
    };
    this.page.onLoadFinished = function(status) {
        if (status === "success") {
            var src, test;
            for (var k in self.inject) {
                if (typeof self.inject[k] !== "string") {
                    test = self.page.evaluate(function (variable) {
                        try { return eval("("+variable+")") != null; }
                        catch (e) { return false; }
                    }, self.inject[k][0]);
                    src = self.inject[k][1];
                } else {
                    src = self.inject[k];
                    test = true;
                }
                if(test && !page.injectJs(src)) {
                    self.error("Can't inject " + src);
                }
            }
        }
    };
    setTimeout(function () {
        self.page.evaluate(function () {
            var message = ("Timeout\nhref: " + window.location.href
                + "\nreferrer: " + document.referrer
                + "\n\n" + document.body.innerHTML).replace(/[^a-z0-9\s~!@#$%^&*()_|+\-=?;:'",.<>\{\}\[\]\\\/]/gi, "*");
            self.error(message);
        });
    }, self.timeout);

    // ----------------------------------------------------
    // run test
    // ----------------------------------------------------
    this.run = function(url_path, code, ready) {
        if(self.options.login) {
            qp = [];
            qp.push('db=' + self.options.db);
            qp.push('login=' + self.options.login);
            qp.push('key=' + self.options.password);
            qp.push('redirect=' + encodeURIComponent(url_path));
            var url_path = "/login?" + qp.join('&');
        }
        var url = self.origin + url_path;
        self.page.open(url, function(status) {
            if (status !== 'success') {
                self.error("failed to load " + url)
            } else {
                console.log('loaded', url, status);
                // process ready
                waitFor(function() {
                    return self.page.evaluate(function (ready) { 
                        var r = false;
                        try {
                            r = !!eval(ready);
                        } catch(ex) {
                            console.log("waiting for " + ready)
                        };
                        return r;
                    }, ready);
                // run test
                }, function() {
                    self.page.evaluate(function (code) { return eval(code); }, code);
                });
            }
        });
    };
}

// js mode or jsfile mode
if(phantom.args.length === 1) {
    pt = new PhantomTest();
    pt.run(pt.options.url_path, pt.options.code, pt.options.ready);
}

// vim:et:
