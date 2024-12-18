import { registry } from "@web/core/registry";

import { productCatalogKanbanView } from "@product/product_catalog/kanban_view";
import { PurchaseProductCatalogKanbanRenderer } from "./kanban_renderer.js";

export const purchaseProductCatalogKanbanView = {
    ...productCatalogKanbanView,
    Renderer: PurchaseProductCatalogKanbanRenderer,
};

registry.category("views").add("purchase_product_kanban_catalog", purchaseProductCatalogKanbanView);
