/** @odoo-module **/

import { registry } from "@web/core/registry";
import { currencies } from "@web/core/currency";
import { UPDATE_METHODS } from "@web/core/orm_service";

export const currencyService = {
    dependencies: ["rpc"],
    start(env, { rpc }) {
        /**
         * Reload the currencies (initially given in session_info)
         */
        async function reloadCurrencies() {
            const result = await rpc("/web/session/get_session_info");
            for (const k in currencies) {
                delete currencies[k];
            }
            Object.assign(currencies, result);
        }
        env.bus.addEventListener("RPC:RESPONSE", (ev) => {
            const { model, method } = ev.detail.data.params;
            if (model === "res.currency" && UPDATE_METHODS.includes(method)) {
                reloadCurrencies();
            }
        });
    },
};

registry.category("services").add("currency", currencyService);
