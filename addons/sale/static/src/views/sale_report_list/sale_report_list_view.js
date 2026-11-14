import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { SaleReportListRenderer } from "./sale_report_list_renderer";

export const saleReportListView = {
    ...listView,
    Renderer: SaleReportListRenderer,
};

registry.category("views").add("sale_report_list", saleReportListView);
