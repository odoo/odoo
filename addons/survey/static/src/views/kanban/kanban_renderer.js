import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { SurveySurveyActionHelper } from "@survey/views/components/survey_survey_action_helper/survey_survey_action_helper";
import { SurveyKanbanRecord } from "@survey/views/kanban/kanban_record";

export class SurveyKanbanRenderer extends KanbanRenderer {
    static template = "survey.SurveyKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: SurveyKanbanRecord,
        SurveySurveyActionHelper,
    }
};
