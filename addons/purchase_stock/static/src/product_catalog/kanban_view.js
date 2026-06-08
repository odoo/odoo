import { patch } from "@web/core/utils/patch";
import { purchaseProductCatalogKanbanView } from "@purchase/product_catalog/kanban_view";
import { PurchaseSuggestCatalogSearchPanel } from "./search/search_panel";
import { PurchaseStockProductCatalogSearchModel } from "./search/search_model";
import { PurchaseSuggestCatalogKanbanController } from "./kanban_controller";
import { PurchaseSuggestCatalogKanbanModel } from "./kanban_model";

patch(purchaseProductCatalogKanbanView, {
    Controller: PurchaseSuggestCatalogKanbanController,
    SearchPanel: PurchaseSuggestCatalogSearchPanel,
    Model: PurchaseSuggestCatalogKanbanModel,
    SearchModel: PurchaseStockProductCatalogSearchModel,
});
