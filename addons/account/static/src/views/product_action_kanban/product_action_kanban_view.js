import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ProductActionKanbanRenderer } from "./product_action_kanban_renderer";

registry.category("views").add("product_sellable_action_kanban", {
    ...kanbanView,
    Renderer: ProductActionKanbanRenderer,
});
