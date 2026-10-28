import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { RottingKanbanRenderer } from "@mail/js/rotting_mixin/rotting_kanban_renderer";
import { rottingKanbanView } from "@mail/js/rotting_mixin/rotting_kanban_view";
import { registry } from "@web/core/registry";

export class RecruitmentKanbanRecord extends KanbanRecord {
    static template = "hr_recruitment.KanbanRecord";
}

export class RecruitmentKanbanRenderer extends RottingKanbanRenderer {
    static components = {
        ...RottingKanbanRenderer.components,
        KanbanRecord: RecruitmentKanbanRecord,
    };
}

export const rottingRecruitmentKanbanView = {
    ...rottingKanbanView,
    Renderer: RecruitmentKanbanRenderer,
};

registry.category("views").add("rotting_recruitment_kanban", rottingRecruitmentKanbanView);
