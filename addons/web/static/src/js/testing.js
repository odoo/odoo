// Test support structures and methods for OpenERP
openerp.testing = {};
(function (testing) {
    var dependencies = {
        pyeval: [],
        core: ['pyeval'],
        data: ['core'],
        dates: [],
        formats: ['core', 'dates'],
        chrome: ['core'],
        views: ['core', 'data', 'chrome'],
        search: ['views', 'formats'],
        list: ['views', 'data'],
        form: ['data', 'views', 'list', 'formats'],
        list_editable: ['list', 'form', 'data'],
    };

    var initialized = [];
    /**
     * openerp.init is a broken-ass piece of shit, makes it impossible to
     * progressively add modules, using it, retarded openerp_inited flag
     * means the first tests being run get their dependencies loaded
     * (basically just base and web), and for *every other module* the tests
     * run without the dependencies being correctly loaded
     */
    function init(modules) {
        if (!initialized.length) {
            openerp.init(modules);
            initialized = openerp._modules.slice();
            return;
        }
        var to_initialize = _.difference(modules, initialized);
        for (var i = 0; i < to_initialize.length; i++) {
            var modname = to_initialize[i];
            var fct = openerp[modname];
            if (typeof fct === 'function') {
                var module = openerp[modname] = {};
                for(var k in fct) {
                    if (!fct.hasOwnProperty(k)) { continue; }
                    module[k] = fct[k];
                }
                fct(openerp, module)
            }
            initialized.push(modname);
            openerp._modules.push(modname);
        }
    }

    testing.dependencies = window['oe_all_dependencies'] || [];
    testing.current_module = null;
    testing.templates = { };
    testing.add_template = function (name) {
        var xhr = QWeb2.Engine.prototype.get_xhr();
        xhr.open('GET', name, false);
        xhr.send(null);
        (testing.templates[testing.current_module] =
            testing.templates[testing.current_module] || [])
                .push(xhr.responseXML);
    };
    /**
     * Function which does not do anything
     */
    testing.noop = function () { };
    /**
     * Alter provided instance's ``session`` attribute to make response
     * mockable:
     *
     * * The ``responses`` parameter can be used to provide a map of (RPC)
     *   paths (e.g. ``/web/view/load``) to a function returning a response
     *   to the query.
     * * ``instance.session`` grows a ``responses`` attribute which is
     *   a map of the same (and is in fact initialized to the ``responses``
     *   parameter if one is provided)
     *
     * Note that RPC requests to un-mocked URLs will be rejected with an
     * error message: only explicitly specified urls will get a response.
     *
     * Mocked sessions will *never* perform an actual RPC connection.
     *
     * @param instance openerp instance being initialized
     * @param {Object} [responses]
     */
    testing.mockifyRPC = function (instance, responses) {
        var session = instance.session;
        session.responses = responses || {};
        session.rpc = function(url, rparams, options) {
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
    };

    var StackProto = {
        execute: function (fn) {
            var args = [].slice.call(arguments, 1);
            // Warning: here be dragons
            var i = 0, setups = this.setups, teardowns = this.teardowns;
            var d = $.Deferred();

            var succeeded, failed;
            var success = function () {
                succeeded = _.toArray(arguments);
                return teardown();
            };
            var failure = function () {
                // save first failure
                if (!failed) {
                    failed = _.toArray(arguments);
                }
                // chain onto next teardown
                return teardown();
            };

            var setup = function () {
                // if setup to execute
                if (i < setups.length) {
                    var f = setups[i] || testing.noop;
                    $.when(f.apply(null, args)).then(function () {
                        ++i;
                        setup();
                    }, failure);
                } else {
                    $.when(fn.apply(null, args)).then(success, failure);
                }
            };
            var teardown = function () {
                // if teardown to execute
                if (i > 0) {
                    var f = teardowns[--i] || testing.noop;
                    $.when(f.apply(null, args)).then(teardown, failure);
                } else {
                    if (failed) {
                        d.reject.apply(d, failed);
                    } else if (succeeded) {
                        d.resolve.apply(d, succeeded);
                    } else {
                        throw new Error("Didn't succeed or fail?");
                    }
                }
            };
            setup();

            return d;
        },
        push: function (setup, teardown) {
            return _.extend(Object.create(StackProto), {
                setups: this.setups.concat([setup]),
                teardowns: this.teardowns.concat([teardown])
            });
        },
        unshift: function (setup, teardown) {
            return _.extend(Object.create(StackProto), {
                setups: [setup].concat(this.setups),
                teardowns: [teardown].concat(this.teardowns)
            });
        }
    };
    /**
     *
     * @param {Function} [setup]
     * @param {Function} [teardown]
     * @return {*}
     */
    testing.Stack = function (setup, teardown) {
        return _.extend(Object.create(StackProto), {
            setups: setup ? [setup] : [],
            teardowns: teardown ? [teardown] : []
        });
    };

    var db = window['oe_db_info'];
    testing.section = function (name, options, body) {
        if (_.isFunction(options)) {
            body = options;
            options = {};
        }
        _.defaults(options, {
            setup: testing.noop,
            teardown: testing.noop
        });

        QUnit.module(testing.current_module + '.' + name, {_oe: options});
        body(testing['case']);
    };
    testing['case'] = function (name, options, callback) {
        if (_.isFunction(options)) {
            callback = options;
            options = {};
        }

        var module = testing.current_module;
        var module_index = _.indexOf(testing.dependencies, module);
        var module_deps = testing.dependencies.slice(
            // If module not in deps (because only tests, no JS) -> indexOf
            // returns -1 -> index becomes 0 -> replace with ``undefined`` so
            // Array#slice returns a full copy
            0, module_index + 1 || undefined);

        // Serialize options for this precise test case
        var env = QUnit.config.currentModuleTestEnvironment;
        // section setup
        //     case setup
        //         test
        //     case teardown
        // section teardown
        var case_stack = testing.Stack()
            .push(env._oe.setup, env._oe.teardown)
            .push(options.setup, options.teardown);
        var opts = _.defaults({}, options, env._oe);
        // FIXME: if this test is ignored, will still query
        if (opts.rpc === 'rpc' && !db) {
            QUnit.config.autostart = false;
            db = {
                source: null,
                supadmin: null,
                password: null
            };
            var $msg = $('<form style="margin: 0 1em 1em;">')
                .append('<h3>A test needs to clone a database</h3>')
                .append('<h4>Please provide the source clone information</h4>')
                .append('     Source DB: ').append('<input name="source">').append('<br>')
                .append('   DB Password: ').append('<input name="supadmin">').append('<br>')
                .append('Admin Password: ').append('<input name="password">').append('<br>')
                .append('<input type="submit" value="OK"/>')
                .submit(function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    db.source = $msg.find('input[name=source]').val();
                    db.supadmin = $msg.find('input[name=supadmin]').val();
                    db.password = $msg.find('input[name=password]').val();
                    QUnit.start();
                    $.unblockUI();
                });
            $.blockUI({
                message: $msg,
                css: {
                    fontFamily: 'monospace',
                    textAlign: 'left',
                    whiteSpace: 'pre-wrap',
                    cursor: 'default'
                }
            });
        }

        QUnit.test(name, function () {
            var instance = openerp;
            init(module_deps);
            instance.session = new instance.web.Session();
            instance.session.uid = 42;
            if (_.isNumber(opts.asserts)) {
                expect(opts.asserts);
            }

            if (opts.templates) {
                for(var i=0; i<module_deps.length; ++i) {
                    var dep = module_deps[i];
                    var templates = testing.templates[dep];
                    if (_.isEmpty(templates)) { continue; }

                    for (var j=0; j < templates.length; ++j) {
                        instance.web.qweb.add_template(templates[j]);
                    }
                }
            }

            var $fixture = $('#qunit-fixture');

            var mock, async = false;
            switch (opts.rpc) {
            case 'mock':
                async = true;
                testing.mockifyRPC(instance);
                mock = function (spec, handler) {
                    instance.session.responses[spec] = handler;
                };
                break;
            case 'rpc':
                async = true;
                (function () {
                // Bunch of random base36 characters
                var dbname = 'test_' + Math.random().toString(36).slice(2);
                // Add db setup/teardown at the start of the stack
                case_stack = case_stack.unshift(function (instance) {
                    // FIXME hack: don't want the session to go through shitty loading process of everything
                    instance.session.session_init = testing.noop;
                    instance.session.load_modules = testing.noop;
                    instance.session.session_bind();
                    return instance.session.rpc('/web/database/duplicate', {
                        fields: [
                            {name: 'super_admin_pwd', value: db.supadmin},
                            {name: 'db_original_name', value: db.source},
                            {name: 'db_name', value: dbname}
                        ]
                    }).then(function (result) {
                        if (result.error) {
                            return $.Deferred().reject(result.error).promise();
                        }
                        return instance.session.session_authenticate(
                            dbname, 'admin', db.password, true);
                    });
                }, function (instance) {
                    return instance.session.rpc('/web/database/drop', {
                            fields: [
                                {name: 'drop_pwd', value: db.supadmin},
                                {name: 'drop_db', value: dbname}
                            ]
                        }).then(function (result) {
                        if (result.error) {
                            return $.Deferred().reject(result.error).promise();
                        }
                        return result;
                    });
                });
                })();
            }

            // Always execute tests asynchronously
            stop();
            var timeout;
            case_stack.execute(function () {
                var result = callback.apply(null, arguments);
                if (!(result && _.isFunction(result.then))) {
                    if (async) {
                        ok(false, "asynchronous test cases must return a promise");
                    }
                } else {
                    if (!_.isNumber(opts.asserts)) {
                        ok(false, "asynchronous test cases must specify the "
                                + "number of assertions they expect");
                    }
                }

                return $.Deferred(function (d) {
                    $.when(result).then(function () {
                        d.resolve.apply(d, arguments);
                    }, function () {
                        d.reject.apply(d, arguments);
                    });
                    if (async || (result && result.then)) {
                        // async test can be either implicit async (rpc) or
                        // promise-returning
                        timeout = setTimeout(function () {
                            QUnit.config.semaphore = 1;
                            d.reject({message: "Test timed out"});
                        }, 2000);
                    }
                });
            }, instance, $fixture, mock).always(function () {
                if (timeout) { clearTimeout(timeout); }
                start();
            }).fail(function (error) {
                if (options.fail_on_rejection === false) {
                    return;
                }
                var message;
                if (typeof error !== 'object'
                        || typeof error.message !== 'string') {
                    message = JSON.stringify([].slice.apply(arguments));
                } else {
                    message = error.message;
                    if (error.data && error.data.debug) {
                        message += '\n\n' + error.data.debug;
                    }
                }

                ok(false, message);
            });
        });
    };
})(openerp.testing);
