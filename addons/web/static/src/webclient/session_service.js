import { registry } from "@web/core/registry";
import { deepCopy } from "@web/core/utils/objects";

export const lazySession = {
    dependencies: ["orm"],
    start(env, { orm }) {
        let resolveWebClientReady;
        let lazyConfigPromise;
        const fetchServerData = async (params) => {
            await webClientReadyPromise;
            return orm.call("ir.http", "lazy_session_info", [[]], params);
        };
        const webClientReadyPromise = new Promise((r) => (resolveWebClientReady = r));
        env.bus.addEventListener("WEB_CLIENT_READY", resolveWebClientReady);
        return {
            getValue(key, callback, params) {
                if (!lazyConfigPromise) {
                    lazyConfigPromise = fetchServerData(params);
                }
                lazyConfigPromise.then((config) => callback(deepCopy(config)[key]));
            },
            rpcDone: () => !!lazyConfigPromise,
        };
    },
};

registry.category("services").add("lazy_session", lazySession);
