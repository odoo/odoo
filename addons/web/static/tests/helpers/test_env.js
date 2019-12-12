odoo.define('web.test_env', async function (require) {
    "use strict";

    const Bus = require('web.Bus');
    const DebugManager = require('web.DebugManager');
    const { buildQuery } = require('web.rpc');
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
        const defaultEnv = {
            _t: env._t || Object.assign((s => s), { database }),
            _lt: env._lt || Object.assign((s => s), { database }),
            bus: env.bus || new Bus(), // FIXME: never destroyed
            device: Object.assign({ isMobile: false }, env.device),
            isDebug: env.isDebug || (() => false),
            qweb: new owl.QWeb({ templates: session.owlTemplates }),
            services: Object.assign({
                ajax: {
                    rpc() {
                      return env.session.rpc(...arguments); // Compatibility Legacy Widgets
                    }
                },
                getCookie() { },
                rpc(params, options) {
                    const query = buildQuery(params);
                    return env.session.rpc(query.route, query.params, options);
                },
                notification: { notify() { } },
            }, env.services),
            session: Object.assign({
                rpc(route, params, options) {
                    if (providedRPC) {
                        return providedRPC(route, params, options);
                    }
                    throw new Error(`No method to perform RPC`);
                },
                url: session.url,
            }, env.session),
        };
        return Object.assign(env, defaultEnv);
    }

    /**
     * Before each test, we want owl.Component.env to be a fresh test environment.
     */
    QUnit.on('OdooBeforeTestHook', function () {
        owl.Component.env = makeTestEnvironment();

        // In debug mode, the DebugManager is automatically deployed, but we
        // don't want to have it in tests (mainly because it does an RPC).
        // DebugManager tests have to manually deploy it themselves.
        DebugManager.undeploy();
    });

    return makeTestEnvironment;
});
