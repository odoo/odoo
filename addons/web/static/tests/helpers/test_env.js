odoo.define('web.test_env', async function (require) {
    "use strict";

    const AbstractStorageService = require('web.AbstractStorageService');
    const Bus = require("web.Bus");
    const RamStorage = require('web.RamStorage');
    const { buildQuery } = require("web.rpc");
    const session = require('web.session');

    /**
     * Creates a test environment with the given environment object.
     * Any access to a key that has not been explicitly defined in the given environment object
     * will result in an error.
     *
     * @param {Object} [env={}]
     * @param {Function} [providedRPC=null]
     * @returns {Proxy}
     */
    function makeTestEnvironment(env = {}, providedRPC = null) {
        const RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });
        const database = {
            parameters: {
                code: "en_US",
                date_format: '%m/%d/%Y',
                decimal_point: ".",
                direction: 'ltr',
                grouping: [],
                thousands_sep: ",",
                time_format: '%H:%M:%S',
            },
        };
        let testEnv = {};
        const defaultEnv = {
            _t: env._t || Object.assign((s => s), { database }),
            _lt: env._lt || Object.assign((s => s), { database }),
            bus: new Bus(),
            device: Object.assign({ isMobile: false }, env.device),
            isDebug: env.isDebug || (() => false),
            qweb: new owl.QWeb({ templates: session.owlTemplates }),
            services: Object.assign({
                ajax: { // for legacy subwidgets
                    rpc() {
                        const prom = testEnv.session.rpc(...arguments);
                        prom.abort = function () {
                            throw new Error("Can't abort this request");
                        };
                        return prom;
                    },
                },
                getCookie() { },
                rpc(params, options) {
                    const query = buildQuery(params);
                    return testEnv.session.rpc(query.route, query.params, options);
                },
                local_storage: new RamStorageService(),
                session_storage: new RamStorageService(),
                notification: { notify() { } },
            }, env.services),
            session: Object.assign({
                rpc(route, params, options) {
                    if (providedRPC) {
                        return providedRPC(route, params, options);
                    }
                    throw new Error(`No method to perform RPC`);
                },
            }, env.session),
        };
        testEnv = Object.assign(env, defaultEnv);
        return testEnv;
    }

    /**
     * Before each test, we want owl.Component.env to be a fresh test environment.
     */
    QUnit.on('OdooBeforeTestHook', function () {
        owl.Component.env = makeTestEnvironment();
    });

    return makeTestEnvironment;
});
