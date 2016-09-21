
odoo.testing = {};

odoo.testing.MockRPC = function (session) {
    this.responses = {};
};

odoo.testing.MockRPC.prototype.clear = function () {
    this.responses = {};
};

odoo.testing.MockRPC.prototype.interceptRPC = function (session) {
    session.rpc = this.rpc.bind(this);
};

odoo.testing.MockRPC.prototype.add = function (spec, handler, no_override) {
    if (no_override && (spec in this.responses)) {
        return;
    }
    this.responses[spec] = handler;
};

odoo.testing.MockRPC.prototype.rpc =  function (url, rparams, options) {
    if (_.isString(url)) {
        url = {url: url};
    }
    var fn, params;
    var needle = rparams.model + ':' + rparams.method;
    if (url.url.substr(0, 20) === '/web/dataset/call_kw' && needle in this.responses) {
        fn = this.responses[needle];
        params = [
            rparams.args || [],
            rparams.kwargs || {}
        ];
    } else {
        fn = this.responses[url.url];
        params = [{params: rparams}];
    }

    if (!fn) {
        return $.Deferred().reject({}, 'failed',
            _.str.sprintf("Url %s not found in mock responses, with arguments %s",
                          url.url, JSON.stringify(rparams))
        ).promise();
    }
    try {
        return $.when(fn.apply(null, params)).then(function (result) {
            // Wrap for RPC layer unwrapper thingy
            return result;
        });
    } catch (e) {
        // not sure why this looks like that
        return $.Deferred().reject({}, 'failed', String(e));
    }
};

odoo.testing.noop = function () {};

odoo.define_section = function (name, section_deps, section_body) {
    var section_body, options;

    if (typeof arguments[2] === 'function') {
        options = {};
        section_body = arguments[2];
    } else {
        options = arguments[2];
        section_body = arguments[3];
    }

    odoo.subset(function filter (_name) {
            return _name === 'web.core' || _name === 'web.session' || section_deps.indexOf(_name) !== -1;
        })
        .then(function (services) {
            var mock = new odoo.testing.MockRPC();
            if (odoo.testing.templates) {
                services['web.core'].qweb.add_template(odoo.testing.templates);
            }

            function test () {
                var _name = arguments[0],
                    dep_names = arguments[1] instanceof Array ? arguments[1] : [],
                    body = arguments[arguments.length - 1],
                    deps = _.map(section_deps.concat(dep_names), function (name) { return services[name]; });

                QUnit.module(name, options);

                odoo.subset(function filter (_name) { return dep_names.indexOf(_name) !== -1; }, services.subset)
                    .then(function (services) {
                        QUnit.test(_name, function (assert) {
                            mock.clear();
                            mock.interceptRPC(services['web.session']);
                            var info = {
                                'assert': assert,
                                'mock': mock,
                                'deps': _.pick.apply(null, [services].concat(section_deps).concat(dep_names)),
                            };
                            return body.apply(info, [assert].concat(deps));
                        });
                    });
            }
            section_body(test, mock);

        });
};

var time_done;
QUnit.done(function(result) {
    clearTimeout(time_done);
    time_done = setTimeout(function () {
        if (result.failed === 0) {
            console.log('ok');
        } else {
            console.log('error');
        }
    }, 500);
});

QUnit.log(function(result) {
    if (!result.result) {
        console.log(result.name, 'in section', result.module, 'failed:', result.message);
    }
});

(new QWeb2.Engine()).load_xml("/web/webclient/qweb", function (err, xDoc) {
    odoo.testing.templates = xDoc;
    QUnit.start();
});

QUnit.config.autostart = false;


localStorage.clear();
QUnit.config.testTimeout = 1 * 60 * 1000;
QUnit.moduleDone(function(result) {
    if (!result.failed) {
        console.log(result.name, "passed", result.total, "tests.");
    } else {
        console.log(result.name, "failed:", result.failed, "tests out of", result.total, ".");
    }

});
