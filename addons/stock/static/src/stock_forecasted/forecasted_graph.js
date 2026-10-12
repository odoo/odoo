import { registry } from "@web/core/registry";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { graphView } from "@web/views/graph/graph_view";

export class StockForecastedGraphRenderer extends GraphRenderer {
    static template = "stock.ForecastedGraphRenderer";

    getLineChartData() {
        const data = super.getLineChartData();
        // Ensure the line chart is stepped
        data.datasets.forEach((dataset) => {
            dataset.stepped = true;
            dataset.spanGaps = true;
        });
        if (data.datasets.length) {
            const dataset_length = data.datasets[0].data.length;
            for(let i = dataset_length-2; i > 0; i--) { // i=0 and i=last are always preserved
                let skipData = data.datasets.every(d => d.data[i] == d.data[i-1]);
                if (skipData){
                    data.datasets.forEach((dataset) => {
                        dataset.data[i] = null; // Mark as null to indicate it can be skipped
                    });
                }
            }
        }
        return data;
    }
};

export const StockForecastedGraphView = {
    ...graphView,
    Renderer: StockForecastedGraphRenderer,
};

registry.category("views").add("stock_forecasted_graph", StockForecastedGraphView);
