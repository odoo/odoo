import { registry } from "@web/core/registry";

const commandCategoryRegistry = registry.category("command_categories");
// A shortcut conflict occurs when actions are bound to the same
// shortcut as the command palette. To avoid this, those actions can be
// added to the command palette itself within this high priority category
// so that they appear first in the results.
commandCategoryRegistry.add("shortcut_conflict", {}, { sequence: 5 });
