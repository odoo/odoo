/** @odoo-module */

import { registry } from "@web/core/registry";

export const contextService = {
    start() {
        return {};
    },
};
registry.category("services").add("mail.context", contextService);
