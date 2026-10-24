import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const websiteOfflineService = {
    start() {
        return {
            status: reactive({ offline: false }),
            checkConnection() {},
        };
    },
};

registry.category("services").add("offline", websiteOfflineService, { force: true });
