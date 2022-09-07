/** @odoo-module **/

import { listView } from '@web/views/list/list_view';
import { registry } from "@web/core/registry";
import { PurchaseOrderLineCompareListRenderer } from "./purchase_order_line_compare_list_renderer";


export const PurchaseOrderLineCompareListView = {
    ...listView,
    Renderer: PurchaseOrderLineCompareListRenderer,
};

registry.category("views").add("purchase_order_line_compare", PurchaseOrderLineCompareListView);
