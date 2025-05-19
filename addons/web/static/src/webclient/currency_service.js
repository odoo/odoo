import { rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { currencies } from "@web/core/currency";
import { UPDATE_METHODS } from "@web/core/orm_service";

export const currencyService = {
    dependencies: ["orm"],
    async: ["reload_currencies"],
    start(env, { orm }) {
        /**
         * Reload the currencies (initially given in session_info)
         */
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
