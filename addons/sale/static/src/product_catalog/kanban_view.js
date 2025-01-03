import { registry } from "@web/core/registry";
import { SaleProductCatalogKanbanRecord } from "./kanban_record";
import { productCatalogKanbanView } from "@product/product_catalog/kanban_view";
import { ProductCatalogKanbanRenderer } from "@product/product_catalog/kanban_renderer";

export class SaleProductCatalogKanbanRenderer extends ProductCatalogKanbanRenderer {
    static components = {
        ...ProductCatalogKanbanRenderer.components,
        KanbanRecord: SaleProductCatalogKanbanRecord,
    };
}

export const saleProductCatalogKanbanView = {
    ...productCatalogKanbanView,
    Renderer: SaleProductCatalogKanbanRenderer,
};

registry.category("views").add("sale_product_kanban_catalog", saleProductCatalogKanbanView);
