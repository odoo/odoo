import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

const originalRPC = rpc._rpc;
rpc._rpc = function (route, params, settings) {
    if (!route.match(/^(?:https?:)?\/\//)) {
        route = window.location.origin + route;
    }
    const portalEl = document.querySelector(".o_portal_chatter");
    if (!route.match(/^(?:https?:)?\/\//)) {
        route = session.origin + route;
    }
    const routeURL = new URL(route);
    const moduleName = routeURL.pathname.split("/").slice(1)[0];
    if (portalEl && moduleName === "mail") {
        Object.assign(params, {
            portal_token: portalEl.getAttribute("data-token"),
            portal_hash: portalEl.getAttribute("data-hash"),
            portal_pid: parseInt(portalEl.getAttribute("data-pid")),
            portal_res_id: parseInt(portalEl.getAttribute("data-res_id")),
            portal_res_model: portalEl.getAttribute("data-res_model"),
        });
    }
    return originalRPC(route, params, settings);
};
