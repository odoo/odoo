/** @odoo-module **/

import { registry } from "@web/core/registry";

const fakeMenuService = {
    name: "menu",
    start() {
        return {};
    },
};
registry.category("services").add("menu", fakeMenuService);
