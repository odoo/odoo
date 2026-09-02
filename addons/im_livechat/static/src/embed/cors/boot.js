import { expirableStorage } from "@im_livechat/core/common/expirable_storage";
import { GUEST_TOKEN_STORAGE_KEY } from "@im_livechat/embed/common/store_service_patch";
import { livechatRoutingMap } from "@im_livechat/embed/cors/livechat_routing_map";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

(async function boot() {
    const originalFetch = window.fetch;
    window.fetch = function imLivechatMockFetch(input, init) {
        const strInput = String(input);
        if (!/^(?:https?:)?\/\//.test(strInput)) {
            input = session.origin + strInput;
        }
        return originalFetch(input, init);
    };

    // Override rpc to forward requests to CORS-allowed routes.
    // The "guest_token" will be appended to the request parameters for authentication.
    const originalRPC = rpc._rpc;
    rpc._rpc = function (route, params, settings) {
        if (route in livechatRoutingMap.content) {
            route = livechatRoutingMap.get(route, route);
            const guestToken = expirableStorage.getItem(GUEST_TOKEN_STORAGE_KEY);
            if (guestToken) {
                params = {
                    ...params,
                    guest_token: guestToken,
                };
            }
        }
        if (!route.match(/^(?:https?:)?\/\//)) {
            route = session.origin + route;
        }
        return originalRPC(route, params, settings);
    };
    // Remove the error service: it fails to identify issues within the shadow
    // DOM of the live chat and causes disruption for pages that embed it by
    // displaying pop-ups for errors outside of its scope.
    registry.category("services").remove("error");
})();
