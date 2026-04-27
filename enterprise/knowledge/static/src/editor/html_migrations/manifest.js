import { registry } from "@web/core/registry";

// Handle the conversion of `o_knowledge_behavior_anchor` elements to their
// `data-embedded` counterpart, when loading the value of a html_field.
registry
    .category("html_editor_upgrade")
    .category("1.0")
    .add("knowledge", "@knowledge/editor/html_migrations/migration-1.0");
