import { registry } from "@web/core/registry";

import { purchaseProductCatalogKanbanView } from "@purchase/product_catalog/kanban_view";
import { PurchaseSuggestSearchPanel } from "./search/search_panel";


export const purchaseSuggestProductCatalogKanbanView = {
    ...purchaseProductCatalogKanbanView,
    SearchPanel: PurchaseSuggestSearchPanel,
};

registry.category("views").add("purchase_suggest_product_kanban_catalog", purchaseSuggestProductCatalogKanbanView);
