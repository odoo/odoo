/** @odoo-module */

import { ForecastColumnQuickCreate } from '@crm/js/forecast/forecast_kanban_column_quick_create';

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

export class ForecastKanbanRenderer extends KanbanRenderer {
    canCreateGroup() {
        /* YTI: Probably to refine*/
        return true;
    }
};

ForecastKanbanRenderer.components = {
    ...KanbanRenderer.components,
    KanbanColumnQuickCreate: ForecastColumnQuickCreate,
};
