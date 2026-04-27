/** @odoo-module **/
import { registry } from "@web/core/registry";
import { FSMProductCatalogKanbanRecord } from "./kanban_record";
import { FSMProductCatalogKanbanController } from "./kanban_controller";
import { FSMProductCatalogKanbanModel } from "./kanban_model";
import { productCatalogKanbanView } from "@product/product_catalog/kanban_view";
import { ProductCatalogKanbanRenderer } from "@product/product_catalog/kanban_renderer";

export class FSMProductCatalogKanbanRenderer extends ProductCatalogKanbanRenderer {
    static components = {
        ...ProductCatalogKanbanRenderer.components,
        KanbanRecord: FSMProductCatalogKanbanRecord,
    };

    get createProductContext() {
        return { default_invoice_policy: "delivery" };
    }
}

export const fsmProductCatalogKanbanView = {
    ...productCatalogKanbanView,
    Renderer: FSMProductCatalogKanbanRenderer,
    Controller: FSMProductCatalogKanbanController,
    Model: FSMProductCatalogKanbanModel,
};

registry.category("views").add("fsm_product_kanban", fsmProductCatalogKanbanView);
