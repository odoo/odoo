import { registry } from "@web/core/registry";

// Remove the Excalidraw EmbeddedComponent and replace it with a link.
registry
    .category("html_editor_upgrade")
    .category("1.1")
    .add("html_editor", "@html_editor/html_migrations/migration-1.1");
