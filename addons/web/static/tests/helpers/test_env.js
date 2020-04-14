odoo.define('web.test_env', async function (require) {
    "use strict";

    const AbstractStorageService = require('web.AbstractStorageService');
    const Bus = require("web.Bus");
    const RamStorage = require('web.RamStorage');
    const { buildQuery } = require("web.rpc");
    const session = require('web.session');

    /**
     * Wrap the target object in a Proxy, giving it a generic getter that will
     * throw an error instead of returning `undefined` in case the property has
     * not been set.
     *
     * @param {Object} target
     * @param {string} name
     * @returns {Proxy}
     */
    function _proxify(target, name) {
        for (const prop in target) {
            if (
                target.hasOwnProperty(prop) &&
                typeof target[prop] === 'object' &&
                target[prop] !== null
            ) {
                target[prop] = _proxify(target[prop], `${name}.${prop}`);
            }
        }
        return new Proxy(target, {
            get(object, property) {
                if (typeof property === 'string' && !(property in object)) {
                    throw new Error(`Property "${property}" not implemented in "${name}".`);
                }
                return object[property];
            },
        });
    }

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
        const proxiedEnv = _proxify(env, 'env');
        const RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });
        let testEnv = {};
        const defaultEnv = {
            _t: env._t || (s => s),
            _lt: env._lt || (s => s),
            browser: {},
            bus: new Bus(),
            device: Object.assign({
                isMobile: false,
            }, env.device),
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
                httpRequest() {
                    return Promise.resolve('');
                },
                rpc(params, options) {
                    const query = buildQuery(params);
                    return testEnv.session.rpc(query.route, query.params, options);
                },
                local_storage: new RamStorageService(),
                session_storage: new RamStorageService(),
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
        testEnv = Object.assign(proxiedEnv, defaultEnv);
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
