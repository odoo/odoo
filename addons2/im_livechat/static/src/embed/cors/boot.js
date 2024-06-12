/* @odoo-module */

import { livechatRoutingMap } from "@im_livechat/embed/cors/livechat_routing_map";

import { browser } from "@web/core/browser/browser";
import { jsonrpc } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

(async function boot() {
    const { fetch } = browser;
    browser.fetch = function (url, ...args) {
        if (!url.match(/^(?:https?:)?\/\//)) {
            url = session.origin + url;
        }
        return fetch(url, ...args);
    };
    // Override the rpc service to forward requests to CORS-allowed routes. The
    // "guest_token" will be appended to the request parameters for
    // authentication.
    registry.category("services").add(
        "rpc",
        {
            async: true,
            start(env) {
                return function rpc(route, params = {}, settings) {
                    if (route in livechatRoutingMap.content) {
                        route = livechatRoutingMap.get(route, route);
                        if (env.services["im_livechat.livechat"]?.guestToken) {
                            params = {
                                ...params,
                                guest_token: env.services["im_livechat.livechat"].guestToken,
                            };
                        }
                    }
                    if (!route.match(/^(?:https?:)?\/\//)) {
                        route = session.origin + route;
                    }
                    return jsonrpc(route, params, { bus: env.bus, ...settings });
                };
            },
        },
        { force: true }
    );
    // Remove the error service: it fails to identify issues within the shadow
    // DOM of the live chat and causes disruption for pages that embed it by
    // displaying pop-ups for errors outside of its scope.
    registry.category("services").remove("error");
})();
