/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { useService } from "@web/core/utils/hooks";

import { ProductCatalogKanbanRecord } from "./kanban_record";


export class ProductCatalogKanbanRenderer extends KanbanRenderer {
    static template = "sale.ProductCatalogKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: ProductCatalogKanbanRecord
    };

    setup() {
        super.setup();
        this.action = useService("action");
    }

    async createProduct() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "product.product",
            target: "new",
            views: [[false, "form"]],
            view_mode: "form",
        });
    }
}
