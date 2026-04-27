import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { AppraisalActionHelper } from "@hr_appraisal/views/appraisal_helper_view";

export class AppraisalKanbanRenderer extends KanbanRenderer {
    static template = "hr_appraisal.AppraisalKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        AppraisalActionHelper,
    };
};


export const AppraisalKanbanView = {
    ...kanbanView,
    Renderer: AppraisalKanbanRenderer,
};

registry.category("views").add("appraisal_kanban_view", AppraisalKanbanView);
