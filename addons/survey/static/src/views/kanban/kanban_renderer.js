import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { SurveyKanbanRecord } from "@survey/views/kanban/kanban_record";

export class SurveyKanbanRenderer extends KanbanRenderer {
    static template = "survey.SurveyKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: SurveyKanbanRecord,
    }
};
