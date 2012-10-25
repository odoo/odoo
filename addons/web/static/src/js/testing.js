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

    var _load = function (instance, module, loaded) {
        if (!loaded) { loaded = []; }

        var deps = dependencies[module];
        if (!deps) { throw new Error("Unknown dependencies for " + module); }

        var to_load = _.difference(deps, loaded);
        while (!_.isEmpty(to_load)) {
            _load(instance, to_load[0], loaded);
            to_load = _.difference(deps, loaded);
        }
        openerp.web[module](instance);
        loaded.push(module);
    };

    testing.section = function (name, body) {
        QUnit.module(testing.current_module + '.' + name);
        body(testing.case);
    };
    testing.case = function (name, options, callback) {
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
        QUnit.test(name, function (env) {
            var instance = openerp.init(module_deps);
            if (_.isNumber(options.asserts)) {
                expect(options.asserts)
            }

            if (options.templates) {
                for(var i=0; i<module_deps.length; ++i) {
                    var dep = module_deps[i];
                    var templates = testing.templates[dep];
                    if (_.isEmpty(templates)) { continue; }

                    for (var j=0; j < templates.length; ++j) {
                        instance.web.qweb.add_template(templates[j]);
                    }
                }
            }

            var mock, async = false;
            switch (options.rpc) {
            case 'mock':
                async = true;
                testing.mockifyRPC(instance);
                mock = function (spec, handler) {
                    instance.session.responses[spec] = handler;
                };
                break;
            case 'rpc':
                async = true;
            }

            // TODO: explicit dependencies options for web sub-modules (will deprecate _load/instanceFor)
            var result = callback(instance, $('#qunit-fixture'), mock);

            if (!(result && _.isFunction(result.then))) {
                if (async) {
                    ok(false, "asynchronous test cases must return a promise");
                }
                return;
            }

            stop();
            if (!_.isNumber(options.asserts)) {
                ok(false, "asynchronous test cases must specify the "
                        + "number of assertions they expect");
            }
            result.then(function () {
                start();
            }, function (error) {
                start();
                if (options.fail_on_rejection === false) {
                    return;
                }
                ok(false, typeof error === 'object' && error.message
                            ? error.message
                            : JSON.stringify([].slice.call(arguments)));
            })
        });
    };
})(openerp.testing);
