import { registry } from "@web/core/registry";

import { productCatalogKanbanView } from "@product/product_catalog/kanban_view";
import { SaleProductCatalogKanbanModel } from "./kanban_model.js";

export const saleProductCatalogKanbanView = {
    ...productCatalogKanbanView,
    Model: SaleProductCatalogKanbanModel,
};

registry.category("views").add("sale_product_kanban_catalog", saleProductCatalogKanbanView);
