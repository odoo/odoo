/* @odoo-module */

import { registry } from "@web/core/registry";
import { DiscussChannelAttachmentKanbanController } from "@im_livechat/views/discuss_channel_attachment_kanban/discuss_channel_attachment_kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";

const discussChannelAttachmentKanban = {
    ...kanbanView,
    Controller: DiscussChannelAttachmentKanbanController,
};

registry
    .category("views")
    .add("im_livechat.discuss_channel_attachment_kanban", discussChannelAttachmentKanban);
