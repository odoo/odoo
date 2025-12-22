/* @odoo-module */

import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { useState } from "@odoo/owl";
import { ProjectTaskKanbanCompiler } from "./project_task_kanban_compiler";
import { SubtaskKanbanList } from "@project/components/subtask_kanban_list/subtask_kanban_list"

export class ProjectTaskKanbanRecord extends KanbanRecord {
    static Compiler = ProjectTaskKanbanCompiler;
    static components = {
        ...KanbanRecord.components,
        SubtaskKanbanList,
    };

    setup() {
        super.setup();
        this.state = useState({folded: true});
    }

    /**
     * @override
     */
    get renderingContext() {
        const context = super.renderingContext;
        context["state"] = this.state;
        return context;
    }
}
