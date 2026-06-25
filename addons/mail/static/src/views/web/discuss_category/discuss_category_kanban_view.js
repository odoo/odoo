import { registry } from "@web/core/registry";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";

export const discussCategoryKanbanView = {
    ...kanbanView,
    Renderer: class DiscussCategoryKanbanRenderer extends KanbanRenderer {
        static template = "mail.DiscussCategoryKanbanRenderer";

        get showNoContentHelper() {
            return (
                !this.props.list.model.root.groups || this.props.list.model.root.groups.length === 0
            );
        }
    },
};

registry.category("views").add("discuss_category_kanban", discussCategoryKanbanView);
