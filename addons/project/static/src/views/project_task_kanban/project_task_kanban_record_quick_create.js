/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
import { KanbanRecordQuickCreate } from "@web/views/kanban/kanban_record_quick_create";
import { ProjectTaskKanbanShortcutsDialog } from "./project_task_kanban_shortcuts_dialog";

export class ProjectTaskKanbanRecordQuickCreate extends KanbanRecordQuickCreate {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    showTips() {
        this.dialog.add(ProjectTaskKanbanShortcutsDialog);
    }
}

ProjectTaskKanbanRecordQuickCreate.template = "project.ProjectTaskKanbanRecordQuickCreate";
