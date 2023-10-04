/** @odoo-module **/

    import Bus from "@web/legacy/js/core/bus";
    import { templates } from "@web/core/assets";
    import { renderToString } from "@web/core/utils/render";
    import { App, Component } from "@odoo/owl";

    let app;

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
        if (!app) {
            app = new App(null, { templates, test: true });
            renderToString.app = app;
        }

        function rpc(route, params, options) {
            if (providedRPC) {
                return providedRPC(route, params, options);
            }
            throw new Error(`No method to perform RPC`);
        }

        const defaultEnv = {
            bus: env.bus || new Bus(),
            debug: env.debug || false,
            services: {
                httpRequest(/* route, params = {}, readMethod = 'json' */) {
                    return Promise.resolve('');
                },
                hotkey: { add: () => () => {} }, // fake service
                notification: { notify() {} },
                rpc,
                ui: { activeElement: document }, // fake service
                ...env.services,
            },
        };
        return Object.assign(env, defaultEnv);
    }

    /**
     * Before each test, we want Component.env to be a fresh test environment.
     */
    QUnit.on('OdooBeforeTestHook', function () {
        Component.env = makeTestEnvironment();
    });

    export default makeTestEnvironment;
