import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { SurveySurveyActionHelper } from "@survey/views/components/survey_survey_action_helper/survey_survey_action_helper";

export class SurveyKanbanRenderer extends KanbanRenderer {
    static template = "survey.SurveyKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        SurveySurveyActionHelper,
    }
};
