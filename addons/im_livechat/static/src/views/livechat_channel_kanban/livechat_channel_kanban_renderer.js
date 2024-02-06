/* @odoo-module */

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { LivechatChannelKanbanRecord } from "./livechat_channel_kanban_record";
import { onWillUnmount } from "@odoo/owl";

export class LivechatChannelKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: LivechatChannelKanbanRecord,
    };

    setup() {
        super.setup(...arguments);
        this.env.services["bus_service"].subscribe("mail.record/insert", (payload) => {
            if (payload.LivechatChannel) {
                this.props.list.load();
            }
        });
        onWillUnmount(() => this.env.services["bus_service"].unsubscribe("mail.record/insert"));
    }
}
