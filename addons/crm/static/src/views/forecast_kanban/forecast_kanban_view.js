/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ForecastKanbanRenderer } from "@crm/views/forecast_kanban/forecast_kanban_renderer";
import { ForecastSearchModel } from "@crm/views/forecast_search_model";
import { ForecastKanbanModel } from "@crm/views/forecast_kanban/forecast_kanban_model";

export const forecastKanbanView = {
    ...kanbanView,
    Model: ForecastKanbanModel,
    Renderer: ForecastKanbanRenderer,
    SearchModel: ForecastSearchModel,
};

registry.category("views").add("forecast_kanban", forecastKanbanView);
