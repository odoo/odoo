import { registry } from '@web/core/registry';
import { ListRenderer } from "@web/views/list/list_renderer";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { listView } from '@web/views/list/list_view';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { SurveyTypeActionHelper } from "@survey/views/components/survey_type_action_helper/survey_type_action_helper";

export class SurveyListRenderer extends ListRenderer {
    static template = "survey.SurveyTypeListRenderer";
    static components = {
        ...ListRenderer.components,
        SurveyTypeActionHelper,
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
        SurveyTypeActionHelper,
    }
};

registry.category('views').add('survey_view_kanban', {
    ...kanbanView,
    Renderer: SurveyKanbanRenderer,
});
