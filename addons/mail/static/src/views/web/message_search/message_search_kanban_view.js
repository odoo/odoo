import { focusNextWrappedCard } from "@mail/views/web/kanban_wrapped_cards";

import { registry } from "@web/core/registry";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";

export class MessageSearchKanbanRenderer extends KanbanRenderer {
    static template = "mail.MessageSearchKanbanRenderer";

    /** @override */
    focusNextCard(area, direction) {
        if (!this.props.list.isGrouped) {
            return super.focusNextCard(area, direction);
        }
        return focusNextWrappedCard(area, direction);
    }
}

export const messageSearchKanbanView = {
    ...kanbanView,
    Renderer: MessageSearchKanbanRenderer,
};

registry.category("views").add("mail_message_search_kanban", messageSearchKanbanView);
