
odoo.testing = {};

odoo.testing.start_services = function () {
    var factories = odoo.__DEBUG__.factories;
    var jobs = _.map(factories, function (factory, name) {
        return {
            name: name,
            factory: factory,
            deps: factory.deps,
        };
    });
    var services = Object.create({
        qweb: new QWeb2.Engine(),
        $: $,
        _: _,
    });
  return odoo.process_jobs(jobs, services);
};

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

odoo.define_section = function (name, section_deps) {
    var section_body, options, mock;

    if (typeof arguments[2] === 'function') {
        options = {};
        section_body = arguments[2];
    } else {
        options = arguments[2];
        section_body = arguments[3];
    }

    QUnit.module(name, options);


    function test () { 
        var name = arguments[0], 
            dep_names = arguments[1] instanceof Array ? arguments[1] : [], 
            body = arguments[arguments.length - 1];

        QUnit.test(name, function (assert) {
            var services = odoo.testing.start_services();
            var deps = _.map(section_deps.concat(dep_names), function (name) { return services[name]; });
            services.qweb.add_template(odoo.testing.templates);
            mock.clear();
            mock.interceptRPC(services['web.session']);
            var info = {
                assert: assert,
                mock: mock,
                deps: _.pick.apply(null, [services].concat(section_deps).concat(dep_names)),
            }
            return body.apply(info, [assert].concat(deps));
        });
    }

    var mock = new odoo.testing.MockRPC();
    section_body(test, mock);
};


QUnit.done(function(result) {
    if (result.failed === 0) {
        console.log('ok');
    } else {
        console.log('error');
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
    console.log(result.name + " (" + result.passed + "/" + result.total + " passed tests)");
});
// core.qweb.add_template("/web/webclient/qweb");

// odoo.define_section = function (section_name, deps, factory) {

// };

// odoo.define_section('utils_compute_domain', ['web.utils'], function (test, require) {
//     var utils = require('web.utils');

//     test("basic", function )
// });

// // Test support structures and methods for OpenERP
// openerp.testing = {};
// (function (testing) {
//     var dependencies = {
//         pyeval: [],
//         core: ['pyeval'],
//         data: ['core'],
//         dates: [],
//         formats: ['core', 'dates'],
//         chrome: ['core'],
//         views: ['core', 'data', 'chrome'],
//         search: ['views', 'formats'],
//         list: ['views', 'data'],
//         form: ['data', 'views', 'list', 'formats'],
//         list_editable: ['list', 'form', 'data'],
//     };

//     var initialized = [];
//     /**
//      * openerp.init is a broken-ass piece of shit, makes it impossible to
//      * progressively add modules, using it, retarded openerp_inited flag
//      * means the first tests being run get their dependencies loaded
//      * (basically just base and web), and for *every other module* the tests
//      * run without the dependencies being correctly loaded
//      */
//     function init(modules) {
//         if (!initialized.length) {
//             openerp.init(modules);
//             initialized = openerp._modules.slice();
//             return;
//         }
//         var to_initialize = _.difference(modules, initialized);
//         for (var i = 0; i < to_initialize.length; i++) {
//             var modname = to_initialize[i];
//             var fct = openerp[modname];
//             if (typeof fct === 'function') {
//                 var module = openerp[modname] = {};
//                 for(var k in fct) {
//                     if (!fct.hasOwnProperty(k)) { continue; }
//                     module[k] = fct[k];
//                 }
//                 fct(openerp, module)
//             }
//             initialized.push(modname);
//             openerp._modules.push(modname);
//         }
//     }

//     testing.dependencies = window['oe_all_dependencies'] || [];
//     testing.current_module = null;
//     /**
//      * Function which does not do anything
//      */
//     testing.noop = function () { };
//     /**
//      * Alter provided instance's ``session`` attribute to make response
//      * mockable:
//      *
//      * * The ``responses`` parameter can be used to provide a map of (RPC)
//      *   paths (e.g. ``/web/view/load``) to a function returning a response
//      *   to the query.
//      * * ``instance.session`` grows a ``responses`` attribute which is
//      *   a map of the same (and is in fact initialized to the ``responses``
//      *   parameter if one is provided)
//      *
//      * Note that RPC requests to un-mocked URLs will be rejected with an
//      * error message: only explicitly specified urls will get a response.
//      *
//      * Mocked sessions will *never* perform an actual RPC connection.
//      *
//      * @param instance openerp instance being initialized
//      * @param {Object} [responses]
//      */
//     testing.mockifyRPC = function (instance, responses) {
//         var session = instance.session;
//         session.responses = responses || {};
//         session.rpc = function(url, rparams, options) {
//             if (_.isString(url)) {
//                 url = {url: url};
//             }
//             var fn, params;
//             var needle = rparams.model + ':' + rparams.method;
//             if (url.url.substr(0, 20) === '/web/dataset/call_kw' && needle in this.responses) {
//                 fn = this.responses[needle];
//                 params = [
//                     rparams.args || [],
//                     rparams.kwargs || {}
//                 ];
//             } else {
//                 fn = this.responses[url.url];
//                 params = [{params: rparams}];
//             }

//             if (!fn) {
//                 return $.Deferred().reject({}, 'failed',
//                     _.str.sprintf("Url %s not found in mock responses, with arguments %s",
//                                   url.url, JSON.stringify(rparams))
//                 ).promise();
//             }
//             try {
//                 return $.when(fn.apply(null, params)).then(function (result) {
//                     // Wrap for RPC layer unwrapper thingy
//                     return result;
//                 });
//             } catch (e) {
//                 // not sure why this looks like that
//                 return $.Deferred().reject({}, 'failed', String(e));
//             }
//         };
//     };

//     var StackProto = {
//         execute: function (fn) {
//             var args = [].slice.call(arguments, 1);
//             // Warning: here be dragons
//             var i = 0, setups = this.setups, teardowns = this.teardowns;
//             var d = $.Deferred();

//             var succeeded, failed;
//             var success = function () {
//                 succeeded = _.toArray(arguments);
//                 return teardown();
//             };
//             var failure = function () {
//                 // save first failure
//                 if (!failed) {
//                     failed = _.toArray(arguments);
//                 }
//                 // chain onto next teardown
//                 return teardown();
//             };

//             var setup = function () {
//                 // if setup to execute
//                 if (i < setups.length) {
//                     var f = setups[i] || testing.noop;
//                     $.when(f.apply(null, args)).then(function () {
//                         ++i;
//                         setup();
//                     }, failure);
//                 } else {
//                     $.when(fn.apply(null, args)).then(success, failure);
//                 }
//             };
//             var teardown = function () {
//                 // if teardown to execute
//                 if (i > 0) {
//                     var f = teardowns[--i] || testing.noop;
//                     $.when(f.apply(null, args)).then(teardown, failure);
//                 } else {
//                     if (failed) {
//                         d.reject.apply(d, failed);
//                     } else if (succeeded) {
//                         d.resolve.apply(d, succeeded);
//                     } else {
//                         throw new Error("Didn't succeed or fail?");
//                     }
//                 }
//             };
//             setup();

//             return d;
//         },
//         push: function (setup, teardown) {
//             return _.extend(Object.create(StackProto), {
//                 setups: this.setups.concat([setup]),
//                 teardowns: this.teardowns.concat([teardown])
//             });
//         },
//         unshift: function (setup, teardown) {
//             return _.extend(Object.create(StackProto), {
//                 setups: [setup].concat(this.setups),
//                 teardowns: [teardown].concat(this.teardowns)
//             });
//         }
//     };
//     /**
//      *
//      * @param {Function} [setup]
//      * @param {Function} [teardown]
//      * @return {*}
//      */
//     testing.Stack = function (setup, teardown) {
//         return _.extend(Object.create(StackProto), {
//             setups: setup ? [setup] : [],
//             teardowns: teardown ? [teardown] : []
//         });
//     };

//     testing.section = function (name, options, body) {
//         if (_.isFunction(options)) {
//             body = options;
//             options = {};
//         }
//         _.defaults(options, {
//             setup: testing.noop,
//             teardown: testing.noop
//         });

//         QUnit.module(name, {_oe: options});
//         body(testing['case']);
//     };
//     testing['case'] = function (name, options, callback) {
//         if (_.isFunction(options)) {
//             callback = options;
//             options = {};
//         }

//         var module = testing.current_module;
//         var module_index = _.indexOf(testing.dependencies, module);
//         var module_deps = testing.dependencies.slice(
//             // If module not in deps (because only tests, no JS) -> indexOf
//             // returns -1 -> index becomes 0 -> replace with ``undefined`` so
//             // Array#slice returns a full copy
//             0, module_index + 1 || undefined);

//         // Serialize options for this precise test case
//         var env = QUnit.config.currentModuleTestEnvironment;
//         // section setup
//         //     case setup
//         //         test
//         //     case teardown
//         // section teardown
//         var case_stack = testing.Stack()
//             .push(env._oe.setup, env._oe.teardown)
//             .push(options.setup, options.teardown);
//         var opts = _.defaults({}, options, env._oe);

//         QUnit.test(name, function () {
//             var instance = openerp;
//             init(module_deps);
//             instance.session = new instance.web.Session();
//             instance.session.uid = 42;
//             if (_.isNumber(opts.asserts)) {
//                 expect(opts.asserts);
//             }

//             var $fixture = $('#qunit-fixture');

//             var mock, async = false;
//             switch (opts.rpc) {
//             case 'mock':
//                 async = true;
//                 testing.mockifyRPC(instance);
//                 mock = function (spec, handler) {
//                     instance.session.responses[spec] = handler;
//                 };
//                 break;
//             }

//             // Always execute tests asynchronously
//             stop();
//             var timeout;
//             case_stack.execute(function () {
//                 var result = callback.apply(null, arguments);
//                 if (!(result && _.isFunction(result.then))) {
//                     if (async) {
//                         ok(false, "asynchronous test cases must return a promise");
//                     }
//                 } else {
//                     if (!_.isNumber(opts.asserts)) {
//                         ok(false, "asynchronous test cases must specify the "
//                                 + "number of assertions they expect");
//                     }
//                 }

//                 return $.Deferred(function (d) {
//                     $.when(result).then(function () {
//                         d.resolve.apply(d, arguments);
//                     }, function () {
//                         d.reject.apply(d, arguments);
//                     });
//                     if (async || (result && result.then)) {
//                         // async test can be either implicit async (rpc) or
//                         // promise-returning
//                         timeout = setTimeout(function () {
//                             QUnit.config.semaphore = 1;
//                             d.reject({message: "Test timed out"});
//                         }, 2000);
//                     }
//                 });
//             }, instance, $fixture, mock).always(function () {
//                 if (timeout) { clearTimeout(timeout); }
//                 start();
//             }).fail(function (error) {
//                 if (options.fail_on_rejection === false) {
//                     return;
//                 }
//                 var message;
//                 if (typeof error !== 'object'
//                         || typeof error.message !== 'string') {
//                     message = JSON.stringify([].slice.apply(arguments));
//                 } else {
//                     message = error.message;
//                     if (error.data && error.data.debug) {
//                         message += '\n\n' + error.data.debug;
//                     }
//                 }

//                 ok(false, message);
//             });
//         });
//     };
// })(openerp.testing);
