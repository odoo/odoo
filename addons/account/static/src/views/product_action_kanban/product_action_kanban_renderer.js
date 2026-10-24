import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { ProductActionHelper } from "@product/js/views/product_action_helper/product_action_helper";

export class ProductActionKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        ActionHelper: ProductActionHelper,
    };
}
