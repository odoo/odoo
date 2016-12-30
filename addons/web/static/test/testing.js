
odoo.testing = {};

odoo.testing.start_services = function () {
    var factories = odoo.__DEBUG__.factories;
    delete factories['mail.chat_manager'];
    var jobs = _.map(factories, function (factory, name) {
        return {
            name: name,
            factory: factory,
            deps: factory.deps,
        };
    });
    var services = Object.create({});
  return odoo.process_jobs(jobs, services);
};

odoo.testing.MockRPC = function (session) {
    this.clear();
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

odoo.define_section = function (name, section_deps) {
    var section_body, options, mock;

    if (typeof arguments[2] === 'function') {
        options = {};
        section_body = arguments[2];
    } else {
        options = arguments[2];
        section_body = arguments[3];
    }

    mock = new odoo.testing.MockRPC();

    function dummyfunc ()  {};

    function beforeEach(assert) {
        var services = odoo.testing.start_services();
        this.deps = services;
        this.getServiceDeps = function getServiceDeps(dep_names) {
            return _.map(dep_names, function (name) { return services[name]; })
        }
        services['web.core'].qweb.add_template(odoo.testing.templates);
        this.mock = mock;
        this.mock.interceptRPC(services['web.session']);
        this.assert = assert;
        (options.beforeEach || dummyfunc).apply(this, [assert].concat(this.getServiceDeps(section_deps)));
    }
    function afterEach(assert) {
        (options.afterEach || dummyfunc).apply(this, [assert].concat(this.getServiceDeps(section_deps)));
        this.mock.clear();
    }

    QUnit.module(name, {
        before: options.before,
        beforeEach: beforeEach,
        afterEach: afterEach,
        after: options.after
    });

    function test () { 
        var name = arguments[0], 
            dep_names = arguments[1] instanceof Array ? arguments[1] : [], 
            body = arguments[arguments.length - 1];

        QUnit.test(name, function (assert) {
            var deps = this.getServiceDeps(section_deps.concat(dep_names));
            return body.apply(this, [assert].concat(deps));
        });
    }

    section_body(test, mock);
};


QUnit.done(function(result) {
    if (result.failed === 0) {
        console.log('ok');
    } else {
        console.log('error');
    }
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
