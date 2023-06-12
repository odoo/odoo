/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { HrRecruitmentKanbanRenderer } from "@hr_recruitment/views/recruitment_kanban_renderer";

export const hrRecruitmentKanbanView = {
    ...kanbanView,
    Renderer: HrRecruitmentKanbanRenderer,
};

registry.category("views").add("recruitment_kanban", hrRecruitmentKanbanView);
