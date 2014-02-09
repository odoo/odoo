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
    this.options = JSON.parse(phantom.args[1]);
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
    // configure page
    // ----------------------------------------------------
    this.page = require('webpage').create();
    this.page.viewportSize = { width: 1366, height: 768 };
    this.page.addCookie({
        'domain': 'localhost',
        'name': 'session_id',
        'value': this.options.session_id,
    });
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
            for (var k in self.inject) {
                if(!page.injectJs(self.inject[k])) {
                    self.error("Can't inject " + self.inject[k]);
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
                            console.log("waiting for page " + ready)
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
    this.run_admin = function(url_path, code, ready) {
        qp = [];
        qp.push('db=' + self.options.db);
        qp.push('login=' + self.options.login);
        qp.push('key=' + self.options.password);
        qp.push('redirect=' + encodeURIComponent(url_path));
        var url_path2 = "/web/login?" + qp.join('&');
        return self.run(url_path2, code, ready);
    };
}

// vim:et:
