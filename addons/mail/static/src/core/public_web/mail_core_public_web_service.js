import { registry } from "@web/core/registry";

export const mailCorePublicWebService = {
    dependencies: ["mail.store", "bus.outdated_page_watcher"],
    /**
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").Services>} services
     */
    start(env, { "mail.store": store, "bus.outdated_page_watcher": watcher }) {
        watcher.subscribe(() => store.reset());
    },
};

registry.category("services").add("mail_core_public_web", mailCorePublicWebService);
