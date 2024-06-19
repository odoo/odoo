import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { RecruitmentActionHelper } from "@hr_recruitment/views/recruitment_helper_view";

export class RecruitmentKanbanRenderer extends KanbanRenderer {
    static template = "hr_recruitment.RecruitmentKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        RecruitmentActionHelper,
    };
}

export const RecruitmentKanbanView = {
    ...kanbanView,
    Renderer: RecruitmentKanbanRenderer,
};

registry.category("views").add("recruitment_kanban_view", RecruitmentKanbanView);
