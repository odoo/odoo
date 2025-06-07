/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { PurchaseDashBoard } from "@purchase/views/purchase_dashboard";

export class PurchaseDashBoardKanbanRenderer extends KanbanRenderer {
    static template = "purchase.PurchaseKanbanView";
    static components = Object.assign({}, KanbanRenderer.components, { PurchaseDashBoard });
}

export const PurchaseDashBoardKanbanView = {
    ...kanbanView,
    Renderer: PurchaseDashBoardKanbanRenderer,
};

registry.category("views").add("purchase_dashboard_kanban", PurchaseDashBoardKanbanView);
