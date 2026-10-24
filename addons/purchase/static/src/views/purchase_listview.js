import { registry } from "@web/core/registry";
import { PurchaseDashBoard } from "@purchase/views/purchase_dashboard";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";

export class PurchaseDashBoardRenderer extends ListRenderer {
    static template = "purchase.ListRenderer";
    static components = Object.assign({}, ListRenderer.components, { PurchaseDashBoard });
}

export const PurchaseDashBoardListView = {
    ...listView,
    Renderer: PurchaseDashBoardRenderer,
};

registry.category("views").add("purchase_dashboard_list", PurchaseDashBoardListView);
