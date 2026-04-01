import { registry } from "@web/core/registry";

// See `HtmlUpgradeManager` docstring for usage details.
const html_upgrade = registry.category("html_editor_upgrade");

// Introduction of embedded components based on Knowledge Behaviors (Odoo 18).
html_upgrade.category("1.0");

// Remove the Excalidraw EmbeddedComponent and replace it with a link.
html_upgrade.category("1.1").add("html_editor", "@html_editor/html_migrations/migration-1.1");

// Fix Banner classes to properly handle `contenteditable` attribute
html_upgrade.category("1.2").add("html_editor", "@html_editor/html_migrations/migration-1.2");

// Knowledge embeddedViews favorite irFilters should have a `user_ids` property.
html_upgrade.category("2.0");
