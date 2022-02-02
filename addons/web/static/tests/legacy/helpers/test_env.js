odoo.define('web.test_env', async function (require) {
    "use strict";

    const Bus = require('web.Bus');
    const { buildQuery } = require('web.rpc');
    const session = require('web.session');

    const { renderToString } = require('@web/core/utils/render');
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
            app = new App(null, { templates: window.__ODOO_TEMPLATES__ });
            renderToString.app = app;
        }

        const defaultTranslationParamters = {
            code: "en_US",
            date_format: '%m/%d/%Y',
            decimal_point: ".",
            direction: 'ltr',
            grouping: [],
            thousands_sep: ",",
            time_format: '%H:%M:%S',
        };

        let _t;
        if ('_t' in env) {
            _t = Object.assign(env._t, {database: env._t.database || {}})
        } else {
            _t = Object.assign(((s) => s), { database: {} });
        }

        _t.database.parameters = Object.assign(defaultTranslationParamters, _t.database.parameters);

        const defaultEnv = {
            _t,
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
            device: Object.assign({
                isMobile: false,
                SIZES: { XS: 0, VSM: 1, SM: 2, MD: 3, LG: 4, XL: 5, XXL: 6 },
            }, env.device),
            isDebug: env.isDebug || (() => false),
            services: Object.assign({
                ajax: {
                    rpc() {
                      return env.session.rpc(...arguments); // Compatibility Legacy Widgets
                    },
                    loadLibs() {}
                },
                getCookie() {},
                httpRequest(/* route, params = {}, readMethod = 'json' */) {
                    return Promise.resolve('');
                },
                rpc(params, options) {
                    const query = buildQuery(params);
                    return env.session.rpc(query.route, query.params, options);
                },
                notification: { notify() { } },
                hotkey: { add: () => () => {} }, // fake service
                ui: { activeElement: document }, // fake service
            }, env.services),
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

    return makeTestEnvironment;
});
