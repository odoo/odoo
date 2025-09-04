import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { SurveyKanbanRenderer } from "@survey/views/kanban/kanban_renderer";

export const SurveyKanbanView = {
    ...kanbanView,
    Renderer: SurveyKanbanRenderer,
};

registry.category('views').add('survey_view_kanban', SurveyKanbanView);
