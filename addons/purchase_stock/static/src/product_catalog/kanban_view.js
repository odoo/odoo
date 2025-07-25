import { patch } from "@web/core/utils/patch";
import { purchaseProductCatalogKanbanView } from "@purchase/product_catalog/kanban_view";
import { PurchaseSuggestCatalogSearchPanel } from "./search/search_panel";
import { PurchaseSuggestCatalogKanbanController } from "./kanban_controller";

patch(purchaseProductCatalogKanbanView, {
    Controller: PurchaseSuggestCatalogKanbanController,
    SearchPanel: PurchaseSuggestCatalogSearchPanel,
});
