import { Cache } from "@web/core/utils/cache";
import { registry } from "@web/core/registry";
import { rpcBus } from "@web/core/network/rpc";

export const modelDisplayNameService = {
    dependencies: ["orm"],
    async: ["getModelDisplayName"],
    start(env, { orm }) {
        const cache = new Cache(
            (model) =>
                orm
                    .call("ir.model", "display_name_for", [[model]])
                    .then((result) => result[0]?.display_name)
                    .catch((error) => {
                        cache.clear(model);
                        return Promise.reject(error);
                    }),
            (model) => model
        );

        rpcBus.addEventListener("CLEAR-CACHES", () => cache.invalidate());

        /**
         * @param {string} model
         * @returns {Promise<object>}
         */
        async function getModelDisplayName(model) {
            if (typeof model !== "string" || !model) {
                throw new Error(`Invalid model name: ${model}`);
            }
            return cache.read(model);
        }

        return { getModelDisplayName };
    },
};

registry.category("services").add("modelDisplayName", modelDisplayNameService);
