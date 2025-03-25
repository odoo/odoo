import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";

import { ProductCatalogKanbanController } from "./kanban_controller";
import { ProductCatalogKanbanModel } from "./kanban_model";
import { ProductCatalogKanbanRenderer } from "./kanban_renderer";
import { ProductCatalogSearchModel } from "./search/search_model";
import { ProductCatalogSearchPanel} from "./search/search_panel";


export const productCatalogKanbanView = {
    ...kanbanView,
    Controller: ProductCatalogKanbanController,
    Model: ProductCatalogKanbanModel,
    Renderer: ProductCatalogKanbanRenderer,
    SearchModel: ProductCatalogSearchModel,
    SearchPanel: ProductCatalogSearchPanel,
};

registry.category("views").add("product_kanban_catalog", productCatalogKanbanView);
