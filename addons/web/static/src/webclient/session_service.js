import { registry } from "@web/core/registry";
import { deepCopy } from "@web/core/utils/objects";

export const lazySession = {
    dependencies: ["orm"],
    start(env, { orm }) {
        let resolveWebClientReady;
        let lazyConfigPromise;
        const fetchServerData = async () => {
            await webClientReadyPromise;
            return orm.call("ir.http", "lazy_session_info");
        };
        const webClientReadyPromise = new Promise((r) => (resolveWebClientReady = r));
        env.bus.addEventListener("WEB_CLIENT_READY", resolveWebClientReady, { once: true });
        return {
            getValue(key, callback) {
                if (!lazyConfigPromise) {
                    lazyConfigPromise = fetchServerData();
                }
                lazyConfigPromise.then((config) => callback(deepCopy(config)[key]));
            },
        };
    },
};

registry.category("services").add("lazy_session", lazySession);
