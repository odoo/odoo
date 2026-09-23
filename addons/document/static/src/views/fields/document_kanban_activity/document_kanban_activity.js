/** @odoo-module native */
import { KanbanActivity } from "@mail/views/web/fields/kanban_activity/kanban_activity";
import { registry } from "@web/core/registry";

registry.category("fields").add("documents_kanban_activity", {
    component: KanbanActivity,
    fieldDependencies: KanbanActivity.fieldDependencies,
});
