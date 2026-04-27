import { KanbanActivity } from "@mail/views/web/fields/kanban_activity/kanban_activity";
import { DocumentsActivityButton } from "./documents_activity_button";
import { registry } from "@web/core/registry";

class DocumentsKanbanActivity extends KanbanActivity {
    static components = { ActivityButton: DocumentsActivityButton };
}

const documentsKanbanActivity = {
    component: DocumentsKanbanActivity,
    fieldDependencies: KanbanActivity.fieldDependencies,
};

registry.category("fields").add("documents_kanban_activity", documentsKanbanActivity);
