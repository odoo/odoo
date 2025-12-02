import { ForecastKanbanController } from "@crm/views/forecast_kanban/forecast_kanban_controller";
import { CrmKanbanArchParser } from "@crm/views/crm_kanban/crm_kanban_arch_parser";
import { ForecastKanbanModel } from "@crm/views/forecast_kanban/forecast_kanban_model";
import { ForecastKanbanRenderer } from "@crm/views/forecast_kanban/forecast_kanban_renderer";
import { ForecastSearchModel } from "@crm/views/forecast_search_model";
import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";

export const forecastKanbanView = {
    ...kanbanView,
    ArchParser: CrmKanbanArchParser,
    Model: ForecastKanbanModel,
    Controller: ForecastKanbanController,
    Renderer: ForecastKanbanRenderer,
    SearchModel: ForecastSearchModel,
};

registry.category("views").add("forecast_kanban", forecastKanbanView);
