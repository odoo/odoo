/** @odoo-module **/

import { registry } from "@web/core/registry";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { graphView } from "@web/views/graph/graph_view";

export class StockForecastedGraphRenderer extends GraphRenderer{};
StockForecastedGraphRenderer.template = "stock.ForecastedGraphRenderer";

export const StockForecastedGraphView = {
    ...graphView,
    Renderer: StockForecastedGraphRenderer,
};

registry.category("views").add("stock_forecasted_graph", StockForecastedGraphView);
