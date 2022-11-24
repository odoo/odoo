/** @odoo-module **/
import { registry } from "@web/core/registry";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ProductCatalogKanbanModel } from "./kanban_model";
import { ProductCatalogKanbanRecord } from "./kanban_record";

export class ProductCatalogKanbanRenderer extends KanbanRenderer {
    static components = {...KanbanRenderer.components, KanbanRecord: ProductCatalogKanbanRecord};
}

export const productCatalogKanbanView = {
    ...kanbanView,
    Model: ProductCatalogKanbanModel,
    Renderer: ProductCatalogKanbanRenderer,
};

registry.category("views").add("sale_product_kanban", productCatalogKanbanView);
