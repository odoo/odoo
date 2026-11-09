import { listView } from "@web/views/list/list_view";
import { InventoryReportListModel } from "./inventory_report_list_model";
import { InventoryListRenderer } from "./inventory_report_list_renderer";
import { registry } from "@web/core/registry";

export const InventoryReportListView = {
    ...listView,
    Renderer: InventoryListRenderer,
    Model: InventoryReportListModel,
};

registry.category("views").add('inventory_report_list', InventoryReportListView);
