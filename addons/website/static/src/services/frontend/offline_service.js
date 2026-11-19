import { proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const websiteOfflineService = {
    start() {
        return proxy({
            offline: false,
            checkConnection() {},
        });
    },
};

registry.category("services").add("offline", websiteOfflineService, { force: true });
