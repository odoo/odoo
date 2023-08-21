/** @odoo-module **/

    import Bus from "@web/legacy/js/core/bus";
    import session from "web.session";
    import { makeTestEnvServices } from "@web/../tests/legacy/helpers/test_services";
    import { templates, setLoadXmlDefaultApp } from "@web/core/assets";
    import { renderToString } from "@web/core/utils/render";
    const { App, Component } = owl;

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
            setLoadXmlDefaultApp(app);
        }

        const defaultEnv = {
            browser: Object.assign({
                setTimeout: window.setTimeout.bind(window),
                clearTimeout: window.clearTimeout.bind(window),
                setInterval: window.setInterval.bind(window),
                clearInterval: window.clearInterval.bind(window),
                requestAnimationFrame: window.requestAnimationFrame.bind(window),
                Date: window.Date,
                fetch: (window.fetch || (() => { })).bind(window),
            }, env.browser),
            bus: env.bus || new Bus(),
            debug: env.debug || false,
            services: makeTestEnvServices(env),
            session: Object.assign({
                rpc(route, params, options) {
                    if (providedRPC) {
                        return providedRPC(route, params, options);
                    }
                    throw new Error(`No method to perform RPC`);
                },
                url: session.url,
                getTZOffset: (() => 0),
            }, env.session),
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
