import { Plugin, useListener, usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { deepCopy } from "@web/core/utils/objects";
import { ORM } from "@web/core/orm_plugin";
import { GlobalBusPlugin } from "@web/core/global_bus_plugin";

export class LazySessionPlugin extends Plugin {
    /** @private */
    orm = usePlugin(ORM);
    /** @private */
    bus = usePlugin(GlobalBusPlugin).bus;
    /** @private */
    lazyConfigPromise = null;
    /** @private */
    resolveWebClientReady;
    /** @private */
    webClientReadyPromise = new Promise((r) => (this.resolveWebClientReady = r));

    setup() {
        useListener(this.bus, "WEB_CLIENT_READY", () => this.resolveWebClientReady(), {
            once: true,
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
