/* @odoo-module */

import { rpcService } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

patch(rpcService, {
    start(env) {
        const rpc = super.start(env);
        return (route, params = {}, settings) => {
            if (!route.match(/^(?:https?:)?\/\//)) {
                route = window.location.origin + route;
            }
            const portalEl = document.querySelector(".o_portal_chatter");
            if (portalEl) {
                Object.assign(params, {
                    portal_token: portalEl.getAttribute("data-token"),
                    portal_res_id: portalEl.getAttribute("data-res_id"),
                    portal_res_model: portalEl.getAttribute("data-res_model"),
                });
            }
            return rpc(route, params, settings);
        };
    },
});
registry.category("services").add("rpc", rpcService, { force: true });
