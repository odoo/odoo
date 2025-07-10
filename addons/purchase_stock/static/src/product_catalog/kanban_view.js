import { patch } from "@web/core/utils/patch";
import { purchaseProductCatalogKanbanView } from "@purchase/product_catalog/kanban_view";
import { PurchaseSuggestCatalogSearchPanel } from "./search/search_panel";
import { PurchaseSuggestCatalogKanbanController } from "./kanban_controller";
import { PurchaseSuggestCatalogKanbanRenderer } from "./kanban_renderer";

patch(purchaseProductCatalogKanbanView, {
    Controller: PurchaseSuggestCatalogKanbanController,
    SearchPanel: PurchaseSuggestCatalogSearchPanel,
    Renderer: PurchaseSuggestCatalogKanbanRenderer,
});
