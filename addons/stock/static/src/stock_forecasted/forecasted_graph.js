import { registry } from "@web/core/registry";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { graphView } from "@web/views/graph/graph_view";

export class StockForecastedGraphRenderer extends GraphRenderer {
    static template = "stock.ForecastedGraphRenderer";
};

export const StockForecastedGraphView = {
    ...graphView,
    Renderer: StockForecastedGraphRenderer,
    buttonTemplate: "stock.StockForecastGraphView.Buttons",
};

registry.category("views").add("stock_forecasted_graph", StockForecastedGraphView);
