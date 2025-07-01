import { registry } from "@web/core/registry";

const html_upgrade = registry.category("html_editor_upgrade");

// Remove the Excalidraw EmbeddedComponent and replace it with a link.
html_upgrade.category("1.1").add("html_editor", "@html_editor/html_migrations/migration-1.1");

// Fix Banner classes to properly handle `contenteditable` attribute
html_upgrade.category("1.2").add("html_editor", "@html_editor/html_migrations/migration-1.2");
