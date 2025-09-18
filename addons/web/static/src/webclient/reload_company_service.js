// @ts-check

/** @module @web/webclient/reload_company_service - Service that triggers a page reload when res.company records are modified */

import { browser } from "@web/core/browser/browser";
import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { UPDATE_METHODS } from "@web/services/orm_service";

// reload the page if changes are being done to `res.company`

registry.category("services").add("reloadCompany", {
    dependencies: ["action"],
    /**
     * @param {import("@odoo/owl").OdooEnv} env
     * @param {{ action: import("@web/webclient").actionService }} services
     */
    start(env, { action }) {
        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            const { data, error } = ev.detail;
            const { model, method } = data.params;
            if (!error && model === "res.company" && UPDATE_METHODS.includes(method)) {
                if (!browser.localStorage.getItem("running_tour")) {
                    action.doAction("reload_context");
                }
            }
        });
    },
});
