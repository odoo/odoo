import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { SurveyListRenderer } from "@survey/views/list/list_renderer";

export const SurveyListView = {
    ...listView,
    Renderer: SurveyListRenderer,
};

registry.category('views').add('survey_view_tree', SurveyListView);
