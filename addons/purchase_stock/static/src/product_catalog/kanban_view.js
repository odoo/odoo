import { patch } from "@web/core/utils/patch";
import { purchaseProductCatalogKanbanView } from "@purchase/product_catalog/kanban_view";
import { PurchaseSuggestCatalogSearchPanel } from "./search/search_panel";

patch(purchaseProductCatalogKanbanView, {
    SearchPanel: PurchaseSuggestCatalogSearchPanel,
});
