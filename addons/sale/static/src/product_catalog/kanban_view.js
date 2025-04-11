import { registry } from "@web/core/registry";
import { SaleProductCatalogKanbanRecord } from "./kanban_record";
import { productCatalogKanbanView } from "@product/product_catalog/kanban_view";
import { ProductCatalogKanbanRenderer } from "@product/product_catalog/kanban_renderer";
import { SaleProductCatalogKanbanModel } from "./kanban_model";

export class SaleProductCatalogKanbanRenderer extends ProductCatalogKanbanRenderer {
    static components = {
        ...ProductCatalogKanbanRenderer.components,
        KanbanRecord: SaleProductCatalogKanbanRecord,
    };
}

export const saleProductCatalogKanbanView = {
    ...productCatalogKanbanView,
    Renderer: SaleProductCatalogKanbanRenderer,
    Model: SaleProductCatalogKanbanModel,
};

registry.category("views").add("sale_product_kanban_catalog", saleProductCatalogKanbanView);
