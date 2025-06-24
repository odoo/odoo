import { registry } from '@web/core/registry';
import { ListRenderer } from "@web/views/list/list_renderer";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { listView } from '@web/views/list/list_view';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { SurveySurveyActionHelper } from "@survey/views/components/survey_survey_action_helper/survey_survey_action_helper";

export class SurveyListRenderer extends ListRenderer {
    static template = "survey.SurveyTypeListRenderer";
    static components = {
        ...ListRenderer.components,
        SurveySurveyActionHelper,
    }
};

registry.category('views').add('survey_view_tree', {
    ...listView,
    Renderer: SurveyListRenderer,
});

export class SurveyKanbanRenderer extends KanbanRenderer {
    static template = "survey.SurveyTypeKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        SurveySurveyActionHelper,
    }
};

registry.category('views').add('survey_view_kanban', {
    ...kanbanView,
    Renderer: SurveyKanbanRenderer,
});
