/** @odoo-module **/

import { registry } from "@web/core/registry";

const commandCategoryRegistry = registry.category("command_categories");
commandCategoryRegistry
    .add("app", {}, { sequence: 10 })
    .add("smart_action", {}, { sequence: 15 })
    .add("actions", {}, { sequence: 30 })
    .add("navbar", {}, { sequence: 40 })
    .add("default", {}, { sequence: 100 })
    .add("debug", {}, { sequence: 110 });
