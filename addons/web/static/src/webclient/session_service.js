// @ts-check

/** @module @web/webclient/session_service - Service that lazy-loads additional session info after the web client is ready */

/** Service that lazy-loads session info after the web client is ready. */
import { registry } from "@web/core/registry";
import { deepCopy } from "@web/core/utils/collections/objects";
export const lazySession = {
    dependencies: ["orm"],
    /**
     * @param {import("@odoo/owl").OdooEnv} env
     * @param {{ orm: import("@web/core").ORM }} services
     * @returns {{ getValue: (key: string, callback: (value: any) => void) => void }}
     */
    start(env, { orm }) {
        /** @type {((value?: any) => void) | undefined} */
        let resolveWebClientReady;
        /** @type {Promise<Record<string, any>> | undefined} */
        let lazyConfigPromise;
        /** @returns {Promise<Record<string, any>>} */
        const fetchServerData = async () => {
            await webClientReadyPromise;
            return orm.call("ir.http", "lazy_session_info");
        };
        const webClientReadyPromise = new Promise((r) => (resolveWebClientReady = r));
        env.bus.addEventListener("WEB_CLIENT_READY", resolveWebClientReady, {
            once: true,
        });
        return {
            /**
             * Fetch a lazy session value and pass it to the callback.
             * @param {string} key - Session info key to retrieve
             * @param {(value: any) => void} callback - Called with the value once fetched
             */
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
