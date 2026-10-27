/** @odoo-module */

import { listView } from "@web/views/list/list_view";
import { InventoryReportListModel } from "./inventory_report_list_model";
import { InventoryReportListController } from "./inventory_report_list_controller";
import { registry } from "@web/core/registry";

export const InventoryReportListView = {
    ...listView,
    Model: InventoryReportListModel,
    Controller: InventoryReportListController,
    buttonTemplate: 'InventoryReport.Buttons',
};

registry.category("views").add('inventory_report_list', InventoryReportListView);
