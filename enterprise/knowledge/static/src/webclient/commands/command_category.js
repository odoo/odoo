/** @odoo-module **/

import { registry } from "@web/core/registry";

const commandCategoryRegistry = registry.category("command_categories");
// displays the articles on input "?"
commandCategoryRegistry.add("knowledge_articles", { namespace: "?" }, { sequence: 10 });
// displays the advanced search command on input "?"
commandCategoryRegistry.add("knowledge_extra", { namespace: "?" }, { sequence: 20 });
