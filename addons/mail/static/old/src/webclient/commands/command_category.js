/** @odoo-module **/

import { registry } from "@web/core/registry";

const commandCategoryRegistry = registry.category("command_categories");
commandCategoryRegistry.add("mail", {}, { sequence: 20 });
