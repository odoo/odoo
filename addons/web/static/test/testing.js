
odoo.testing = {};

odoo.testing.MockRPC = function (session) {
    this.responses = {
        '/web/webclient/bootstrap_translations': function () {
            return {lang_parameters: null, modules: {}};
        }
    };
};

odoo.testing.MockRPC.prototype.clear = function () {
    this.responses = {};
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
        var message = _.str.sprintf("Url %s not found in mock responses, with arguments %s",
                          url.url, JSON.stringify(rparams));
        console.error(message);
        return $.Deferred().reject({}, 'failed', message).promise();
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

odoo.testing.MockRPC.prototype.clone = function () {
    var mock = new odoo.testing.MockRPC();
    for (var k in this.responses) {
        mock.responses[k] = this.responses[k];
    }
    return mock;
};

odoo.testing.noop = function () {};

var services_def = {};
var services_template = {};
var services_job = {
    'web.session': {
        name: 'web.session',
        deps: ['web.Session', 'web.core'],
        factory: function (require) {
            "use strict";

            var Session = require('web.Session');
            var core = require('web.core');
            var mockRPC = new odoo.testing.MockRPC();

            var modules = odoo._modules;
            Session = Session.extend({
                load_qweb: function (mods) {
                    if (!services_def[mods]) {
                        services_def[mods] = $.get('/web/webclient/qweb?mods=' + mods).then(function (doc) {services_template[mods] = doc;});
                    }
                    return $.when(services_def[mods]).then(function (doc) {
                        core.qweb.add_template(odoo.testing.templates);
                        if (!services_template[mods]) { return; }
                        core.qweb.add_template(services_template[mods]);
                    });
                },
                rpc: function () {
                    return this.mockRPC.rpc.apply(this.mockRPC, arguments);
                }
            });

            var session = new Session(undefined, undefined, {'modules': modules, 'use_cors': false});
            session.MockRPC = session.mockRPC = mockRPC;
            session.is_bound = session.session_bind();
            return session;
        }
    }
};


odoo.define_section = function (name, section_deps, section_body) {
    var section_body, options;

    if (typeof arguments[2] === 'function') {
        options = {};
        section_body = arguments[2];
    } else {
        options = arguments[2];
        section_body = arguments[3];
    }

    clearTimeout(time_done);

    odoo.subset(section_deps.concat(['web.core', 'web.session']), null, services_job)
        .then(function (services) {
            var session = services['web.session'];

            function test () {
                var _name = arguments[0],
                    dep_names = arguments[1] instanceof Array ? arguments[1] : [],
                    body = arguments[arguments.length - 1];

                clearTimeout(time_done);
                QUnit.module(name, options);

                odoo.subset(dep_names, services.subset)
                    .then(function (services) {
                        QUnit.test(_name, function (assert) {
                            var mock = session.mockRPC = session.MockRPC.clone();

                            var info = {
                                'assert': assert,
                                'mock': mock,
                                'deps': _.pick.apply(null, [services].concat(section_deps).concat(dep_names)),
                            };
                            var deps = _.map(section_deps.concat(dep_names), function (name) { return services[name]; });
                            clearTimeout(time_done);
                            return body.apply(info, [assert].concat(deps).concat([mock]));
                        });
                    });
            }
            section_body(test, session.MockRPC);

        });
};

var time_done;
QUnit.done(function(result) {
    clearTimeout(time_done);
    time_done = setTimeout(function () {
        console.log("Passed tests:", result.passed);
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
QUnit.config.testTimeout = 3 * 1000;
QUnit.moduleDone(function(result) {
    if (!result.failed) {
        console.log(result.name, "passed", result.total, "tests.");
    } else {
        console.log(result.name, "failed:", result.failed, "tests out of", result.total, ".");
    }

});
