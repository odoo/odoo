// @ts-check

/**
 * Registers the default command palette categories with their display sequence.
 * Categories control the ordering of commands in the command palette (Ctrl+K).
 *
 * @module @web/services/commands/command_category
 */

/** @type {import("@web/core/registry").Registry} */
import { registry } from "@web/core/registry";
const commandCategoryRegistry = registry.category("command_categories");
commandCategoryRegistry
    .add("app", {}, { sequence: 10 })
    .add("smart_action", {}, { sequence: 15 })
    .add("actions", {}, { sequence: 30 })
    .add("default", {}, { sequence: 50 })
    .add("view_switcher", {}, { sequence: 100 })
    .add("debug", {}, { sequence: 110 })
    .add("disabled", {});
