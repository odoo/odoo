// import { onWillRender } from "@odoo/owl";
// import { GraphController } from "@web/views/graph/graph_controller";
import { graphView } from "@web/views/graph/graph_view";
import { registry } from "@web/core/registry";
import { StockReportSearchModel } from "../search/stock_report_search_model";
import { StockReportSearchPanel } from '../search/stock_report_search_panel';

// class StockReportGraphController extends GraphController {
    // setup() {
        // super.setup();
        // onWillRender(() => {
            // this.props.display = { ...(this.props.display || {}), controlPanel: {}, searchPanel: true };
        // });
    // }
// }

export const StockReportGraphView = {
    ...graphView,
    // Controller: StockReportGraphController,
    SearchModel: StockReportSearchModel,
    SearchPanel: StockReportSearchPanel,
};

registry.category("views").add("stock_report_graph_view", StockReportGraphView);
