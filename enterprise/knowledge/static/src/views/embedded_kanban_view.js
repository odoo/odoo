/** @odoo-module **/

import { EmbeddedControllersPatch } from "@knowledge/views/embedded_controllers_patch";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";

export class KnowledgeArticleItemsKanbanController extends EmbeddedControllersPatch(
    KanbanController
) {
    /**
     * @override
     * Some actions require write access on the parent article. Disable those actions if the user
     * does not have it.
     */
    setup() {
        super.setup();
        if (!("isEmbeddedReadonly" in this.env) || this.env.isEmbeddedReadonly) {
            ["create", "createGroup", "deleteGroup", "editGroup"].forEach(
                (action) => (this.props.archInfo.activeActions[action] = false)
            );
            this.props.archInfo.groupsDraggable = false;
            this.props.archInfo.activeActions.quickCreate = false;
        }
    }
}

registry.category("views").add("knowledge_article_view_kanban_embedded", {
    ...kanbanView,
    Controller: KnowledgeArticleItemsKanbanController,
});
