// Test support structures and methods for OpenERP
openerp.testing = {};
(function (testing) {
    var dependencies = {
        corelib: [],
        coresetup: ['corelib'],
        data: ['corelib', 'coresetup'],
        dates: [],
        formats: ['coresetup', 'dates'],
        chrome: ['corelib', 'coresetup'],
        views: ['corelib', 'coresetup', 'data', 'chrome'],
        search: ['data', 'coresetup', 'formats'],
        list: ['views', 'data'],
        form: ['data', 'views', 'list', 'formats'],
        list_editable: ['list', 'form', 'data'],
    };

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
        session.rpc_function = function (url, payload) {
            var fn, params;
            var needle = payload.params.model + ':' + payload.params.method;
            if (url.url === '/web/dataset/call_kw'
                && needle in this.responses) {
                fn = this.responses[needle];
                params = [
                    payload.params.args || [],
                    payload.params.kwargs || {}
                ];
            } else {
                fn = this.responses[url.url];
                params = [payload];
            }

            if (!fn) {
                return $.Deferred().reject({}, 'failed',
                    _.str.sprintf("Url %s not found in mock responses, with arguments %s",
                                  url.url, JSON.stringify(payload.params))
                ).promise();
            }
            try {
                return $.when(fn.apply(null, params)).pipe(function (result) {
                    // Wrap for RPC layer unwrapper thingy
                    return {result: result};
                });
            } catch (e) {
                // not sure why this looks like that
                return $.Deferred().reject({}, 'failed', String(e));
            }
        };
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
        body(testing.case);
    };
    testing.case = function (name, options, callback) {
        if (_.isFunction(options)) {
            callback = options;
            options = {};
        }
        _.defaults(options, {
            setup: testing.noop,
            teardown: testing.noop
        });

        var module = testing.current_module;
        var module_index = _.indexOf(testing.dependencies, module);
        var module_deps = testing.dependencies.slice(
            // If module not in deps (because only tests, no JS) -> indexOf
            // returns -1 -> index becomes 0 -> replace with ``undefined`` so
            // Array#slice returns a full copy
            0, module_index + 1 || undefined);

        // Serialize options for this precise test case
        // WARNING: typo is from jquery, do not fix!
        var env = QUnit.config.currentModuleTestEnviroment;
        var opts = _.defaults({
            // section setup
            //     case setup
            //         test
            //     case teardown
            // section teardown
            setup: function () {
                var args = [].slice.call(arguments);
                return $.when(env._oe.setup.apply(null, args))
                    .pipe(function () {
                        return options.setup.apply(null, args);
                    });
            },
            teardown: function () {
                var args = [].slice.call(arguments);
                return $.when(options.teardown.apply(null, args))
                    .pipe(function () {
                        return env._oe.teardown.apply(null, args);
                    });
            }
        }, options, env._oe);
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
            // module testing environment
            var self = this;

            var instance;
            if (!opts.dependencies) {
                instance = openerp.init(module_deps);
            } else {
                // empty-but-specified dependencies actually allow running
                // without loading any module into the instance

                // TODO: clean up this mess
                var d = opts.dependencies.slice();
                // dependencies list should be in deps order, reverse to make
                // loading order from last
                d.reverse();
                var di = 0;
                while (di < d.length) {
                    var m = /^web\.(\w+)$/.exec(d[di]);
                    if (m) {
                        d[di] = m[1];
                    }
                    d.splice.apply(d, [di+1, 0].concat(
                        _(dependencies[d[di]]).reverse()));
                    ++di;
                }

                instance = openerp.init("fuck your shit, don't load anything you cunt");
                _(d).chain()
                    .reverse()
                    .uniq()
                    .each(function (module) {
                        openerp.web[module](instance);
                    });
            }
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
                (function (setup, teardown) {
                // Bunch of random base36 characters
                var dbname = 'test_' + Math.random().toString(36).slice(2);
                opts.setup = function (instance, $s) {
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
                    }).pipe(function (result) {
                        if (result.error) {
                            return $.Deferred().reject(result.error).promise();
                        }
                        return instance.session.session_authenticate(
                            dbname, 'admin', db.password, true);
                    }).pipe(function () {
                        return setup(instance, $s);
                    });
                };
                opts.teardown = function (instance, $s) {
                    return $.when(teardown(instance, $s)).pipe(function () {
                        return instance.session.session_logout()
                    }).pipe(function () {
                        return instance.session.rpc('/web/database/drop', {
                            fields: [
                                {name: 'drop_pwd', value: db.supadmin},
                                {name: 'drop_db', value: dbname}
                            ]
                        });
                    }).pipe(function (result) {
                        if (result.error) {
                            return $.Deferred().reject(result.error).promise();
                        }
                        return result;
                    });
                };
                })(opts.setup, opts.teardown);
            }

            // Always execute tests asynchronously
            stop();
            var timeout;
            var teardown = function () {
                return opts.teardown(instance, $fixture, mock)
            };
            $.when(opts.setup(instance, $fixture, mock))
            .pipe(function () {
                var result = callback(instance, $fixture, mock);
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
                var d = $.Deferred();
                $.when(result).then(function () {
                    d.resolve.apply(d, arguments)
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
                return d.pipe(teardown, teardown);
            }).always(function () {
                if (timeout) {
                    clearTimeout(timeout);
                }
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

                ok(false, "failed!")
                ok(false, message);
            });
        });
    };
})(openerp.testing);
