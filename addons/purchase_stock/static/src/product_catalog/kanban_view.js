import { patch } from "@web/core/utils/patch";
import { purchaseProductCatalogKanbanView } from "@purchase/product_catalog/kanban_view";
import { PurchaseStockProductCatalogSearchPanel } from "./search/search_panel";
import { PurchaseStockProductCatalogSearchModel } from "./search/search_model";
import { PurchaseStockProductCatalogKanbanController } from "./kanban_controller";
import { PurchaseStockProductCatalogKanbanModel } from "./kanban_model";

patch(purchaseProductCatalogKanbanView, {
    Controller: PurchaseStockProductCatalogKanbanController,
    SearchPanel: PurchaseStockProductCatalogSearchPanel,
    Model: PurchaseStockProductCatalogKanbanModel,
    SearchModel: PurchaseStockProductCatalogSearchModel,
});
