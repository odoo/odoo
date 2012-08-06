// Test support structures and methods for OpenERP
openerp.testing = (function () {
    var xhr = QWeb2.Engine.prototype.get_xhr();
    xhr.open('GET', '/web/static/src/xml/base.xml', false);
    xhr.send(null);
    var doc = xhr.responseXML;

    var dependencies = {
        pyeval: [],
        corelib: ['pyeval'],
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

    return {
        /**
         * Function which does not do anything
         */
        noop: function () { },
        /**
         * Loads 'base.xml' template file into qweb for the provided instance
         *
         * @param instance openerp instance being initialized, to load the template file in
         */
        loadTemplate: function (instance) {
            instance.web.qweb.add_template(doc);
        },
        /**
         * Alter provided instance's ``connection`` attribute to make response
         * mockable:
         *
         * * The ``responses`` parameter can be used to provide a map of (RPC)
         *   paths (e.g. ``/web/view/load``) to a function returning a response
         *   to the query.
         * * ``instance,connection`` grows a ``responses`` attribute which is
         *   a map of the same (and is in fact initialized to the ``responses``
         *   parameter if one is provided)
         *
         * Note that RPC requests to un-mocked URLs will be rejected with an
         * error message: only explicitly specified urls will get a response.
         *
         * Mocked connections will *never* perform an actual RPC connection.
         *
         * @param instance openerp instance being initialized
         * @param {Object} [responses]
         */
        mockifyRPC: function (instance, responses) {
            var connection = instance.connection;
            connection.responses = responses || {};
            connection.rpc_function = function (url, payload) {
                var fn = this.responses[url.url + ':' + payload.params.method]
                      || this.responses[url.url];

                if (!fn) {
                    return $.Deferred().reject({}, 'failed',
                        _.str.sprintf("Url %s not found in mock responses, with arguments %s",
                                      url.url, JSON.stringify(payload.params))
                    ).promise();
                }
                return $.when(fn(payload));
            };
        },
        /**
         * Creates an openerp web instance loading the specified module after
         * all of its dependencies.
         *
         * @param {String} module
         * @returns OpenERP Web instance
         */
        instanceFor: function (module) {
            var instance = openerp.init([]);
            this._load(instance, module);
            return instance;
        },
        _load: function (instance, module, loaded) {
            if (!loaded) { loaded = []; }

            var deps = dependencies[module];
            if (!deps) { throw new Error("Unknown dependencies for " + module); }

            var to_load = _.difference(deps, loaded);
            while (!_.isEmpty(to_load)) {
                this._load(instance, to_load[0], loaded);
                to_load = _.difference(deps, loaded);
            }
            openerp.web[module](instance);
            loaded.push(module);
        }
    }
})();
