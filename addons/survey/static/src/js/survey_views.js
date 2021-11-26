/** @odoo-module */

import KanbanView from 'web.KanbanView';
import ListView from 'web.ListView';
import viewRegistry from 'web.view_registry';
import { SurveyKanbanRenderer, SurveyListRenderer } from './survey_renderers.js';

const SurveyKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Renderer: SurveyKanbanRenderer,
    }),
});

const SurveyListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Renderer: SurveyListRenderer,
    }),
});

viewRegistry.add('survey_view_kanban', SurveyKanbanView);
viewRegistry.add('survey_view_tree', SurveyListView);

export {
    SurveyKanbanView,
    SurveyListView,
};
