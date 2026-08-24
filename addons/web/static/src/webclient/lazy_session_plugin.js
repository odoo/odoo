import { onWillDestroy, Plugin, usePlugin } from "@odoo/owl";
import { useEnv } from "@web/owl2/utils";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { deepCopy } from "@web/core/utils/objects";
import { ORM } from "@web/core/orm_plugin";

export class LazySessionPlugin extends Plugin {
    /** @private */
    orm = usePlugin(ORM);
    /** @private */
    env = useEnv();
    /** @private */
    lazyConfigPromise = null;
    /** @private */
    resolveWebClientReady;
    /** @private */
    webClientReadyPromise = new Promise((r) => (this.resolveWebClientReady = r));

    setup() {
        this.env.bus.addEventListener("WEB_CLIENT_READY", this.resolveWebClientReady, {
            once: true,
        });

        onWillDestroy(() => {
            this.env.bus.removeEventListener("WEB_CLIENT_READY", this.resolveWebClientReady);
        });
    }

    /** @private */
    async fetchServerData() {
        await this.webClientReadyPromise;
        return this.orm.call("ir.http", "lazy_session_info");
    }

    getValue(key, callback) {
        if (!this.lazyConfigPromise) {
            this.lazyConfigPromise = this.fetchServerData();
        }
        this.lazyConfigPromise.then((config) => callback(deepCopy(config)[key]));
    }
}

services.add(LazySessionPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the lazy_session service are removed
 * -----------------------------------------------------------------------------
 */
export const lazySessionService = {
    start() {
        return usePlugin(LazySessionPlugin);
    },
};
registry.category("services").add("lazy_session", lazySessionService);
