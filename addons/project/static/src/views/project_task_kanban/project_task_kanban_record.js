import { useState } from "@odoo/owl";
import { ProjectTaskKanbanCompiler } from "./project_task_kanban_compiler";
import { RottingKanbanRecord } from "@mail/js/rotting_mixin/rotting_kanban_record";
import { SubtaskKanbanList } from "@project/components/subtask_kanban_list/subtask_kanban_list"

export class ProjectTaskKanbanRecord extends RottingKanbanRecord {
    static Compiler = ProjectTaskKanbanCompiler;
    static components = {
        ...RottingKanbanRecord.components,
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
