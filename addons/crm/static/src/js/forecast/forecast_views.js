/** @odoo-module */

import ControlPanel from "web.ControlPanel";
import { ForecastKanbanController } from "./forecast_controllers";
import { ForecastKanbanModel } from "./forecast_models";
import { ForecastKanbanRenderer } from "./forecast_renderers";
import { ForecastSearchModel } from "./forecast_search_model";
import { GraphView } from "@web/views/graph/graph_view";
import KanbanView from "web.KanbanView";
import ListView from "web.ListView";
import { PivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";
import viewRegistry from "web.view_registry";

class ForecastGraphView extends GraphView {}
ForecastGraphView.SearchModel = ForecastSearchModel;

registry.category("views").add("forecast_graph", ForecastGraphView);

class ForecastPivotView extends PivotView {}
ForecastPivotView.SearchModel = ForecastSearchModel;

registry.category("views").add("forecast_pivot", ForecastPivotView);

export class ForecastControlPanel extends ControlPanel {}
ForecastControlPanel.modelExtension = "forecast";

const ForecastKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Renderer: ForecastKanbanRenderer,
        Model: ForecastKanbanModel,
        Controller: ForecastKanbanController,
        ControlPanel: ForecastControlPanel,
    }),
});
viewRegistry.add("forecast_kanban", ForecastKanbanView);

const ForecastListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        ControlPanel: ForecastControlPanel,
    }),
});
viewRegistry.add("forecast_list", ForecastListView);

export { ForecastGraphView, ForecastKanbanView, ForecastListView, ForecastPivotView };
