// @ts-check

/** @module @web/webclient/currency_service - Service that auto-reloads currencies when res.currency records are mutated */

import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { currencies } from "@web/services/currency";
import { UPDATE_METHODS } from "@web/services/orm_service";

/** Service that reloads currencies when res.currency records are mutated. */
export const currencyService = {
    dependencies: ["orm"],
    async: ["reload_currencies"],
    /**
     * @param {import("@odoo/owl").OdooEnv} env
     * @param {{ orm: import("@web/core").ORM }} services
     * @returns {{ reloadCurrencies: () => Promise<void> }}
     */
    start(env, { orm }) {
        /** Reload currencies from the server, replacing the in-memory cache. */
        async function reloadCurrencies() {
            const result = await orm.call("res.currency", "get_all_currencies");
            for (const k in currencies) {
                delete currencies[k];
            }
            Object.assign(currencies, result);
        }
        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            const { data, error } = ev.detail;
            const { model, method } = data.params;
            if (!error && model === "res.currency" && UPDATE_METHODS.includes(method)) {
                reloadCurrencies();
            }
        });
        return { reloadCurrencies };
    },
};

registry.category("services").add("currency", currencyService);
