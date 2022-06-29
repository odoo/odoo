/** @odoo-module **/

import { registry } from "@web/core/registry";

const commandCategoryRegistry = registry.category("command_categories");
commandCategoryRegistry.add("shortcut_conflict", {}, { sequence: 5 });
