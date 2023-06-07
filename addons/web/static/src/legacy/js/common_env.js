/** @odoo-module alias=web.commonEnv **/
    
    /**
     * This file defines the common environment, which contains everything that
     * is needed in the env for both the backend and the frontend (Odoo
     * terminology). This module shouldn't be used as is. It should only be
     * imported by the module defining the final env to use (in the frontend or
     * in the backend). For instance, module 'web.env' imports it, adds stuff to
     * it, and exports the final env that is used by the whole webclient
     * application.
     *
     * There should be as much dependencies as possible in the env object. This
     * will allow an easier testing of components. See [1] for more information
     * on environments.
     *
     * [1] https://github.com/odoo/owl/blob/master/doc/reference/environment.md#content-of-an-environment
     */

    import { jsonRpc } from "web.ajax";
    import { device, isDebug } from "web.config";
    import { bus } from "web.core";
    import rpc from "web.rpc";
    import session from "web.session";
    import { _t } from "@web/core/l10n/translation";
    import {getCookie, setCookie} from "web.utils.cookies";

    const browser = {
        clearInterval: window.clearInterval.bind(window),
        clearTimeout: window.clearTimeout.bind(window),
        Date: window.Date,
        fetch: (window.fetch || (() => { })).bind(window),
        Notification: window.Notification,
        requestAnimationFrame: window.requestAnimationFrame.bind(window),
        setInterval: window.setInterval.bind(window),
        setTimeout: window.setTimeout.bind(window),
    };
    Object.defineProperty(browser, 'innerHeight', {
        get: () => window.innerHeight,
    });
    Object.defineProperty(browser, 'innerWidth', {
        get: () => window.innerWidth,
    });

    // Build the basic env
    const env = {
        _t,
        browser,
        bus,
        device,
        isDebug,
        services: {
            ajaxJsonRPC() {
                return jsonRpc(...arguments);
            },
            getCookie() {
                return getCookie(...arguments);
            },
            httpRequest(route, params = {}, readMethod = 'json') {
                const info = {
                    method: params.method || 'POST',
                };
                if (params.method !== 'GET') {
                    const formData = new FormData();
                    for (const key in params) {
                        if (key === 'method') {
                            continue;
                        }
                        const value = params[key];
                        if (Array.isArray(value) && value.length) {
                            for (const val of value) {
                                formData.append(key, val);
                            }
                        } else {
                            formData.append(key, value);
                        }
                    }
                    info.body = formData;
                }
                return fetch(route, info).then(response => response[readMethod]());
            },
            navigate(url, params) {
                window.location = $.param.querystring(url, params);
            },
            reloadPage() {
                window.location.reload();
            },
            rpc(params, options) {
                const query = rpc.buildQuery(params);
                return session.rpc(query.route, query.params, options);
            },
            setCookie() {
                setCookie(...arguments);
            },
        },
        session,
    };

    export default env;
