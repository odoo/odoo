import { listView } from '@web/views/list/list_view';
import { registry } from "@web/core/registry";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { StockReportSearchModel } from "../search/stock_report_search_model";
import { StockReportSearchPanel } from '../search/stock_report_search_panel';


export class StockReportListModel extends RelationalModel {
    setup() {
        super.setup(...arguments);
        // only aggregate the total value when applying groupby
        this.config.fieldsToAggregate = ["total_value"];
    }
}

export const StockReportListView = {
    ...listView,
    Model: StockReportListModel,
    SearchModel: StockReportSearchModel,
    SearchPanel: StockReportSearchPanel,
};

registry.category("views").add("stock_report_list_view", StockReportListView);
