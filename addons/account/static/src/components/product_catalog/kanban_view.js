import { productCatalogKanbanView } from "@product/product_catalog/kanban_view";
import { patch } from "@web/core/utils/patch";
import { AccountProductCatalogSearchModel } from "./search/search_model";
import { AccountProductCatalogSearchPanel} from "./search/search_panel";

patch(productCatalogKanbanView, {
    SearchModel: AccountProductCatalogSearchModel,
    SearchPanel: AccountProductCatalogSearchPanel,
});
