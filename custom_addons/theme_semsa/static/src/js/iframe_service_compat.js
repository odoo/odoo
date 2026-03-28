/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { websiteEditService } from "@website/core/website_edit_service";

patch(websiteEditService, {
    start(env, deps) {
        const service = super.start(env, deps);
        if (service && typeof service.clearRpcCache !== "function") {
            service.clearRpcCache = () => {};
        }
        if (service && typeof service.rpcCache !== "function") {
            service.rpcCache = async (params) => rpc(params.url, params);
        }
        return service;
    },
});
