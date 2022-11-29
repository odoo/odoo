/** @odoo-module */

import { registry } from "@web/core/registry";

const contextService = {
    start() {
        return {
            inPublicPage: true,
        };
    },
};
registry.category("services").add("mail.context", contextService);
