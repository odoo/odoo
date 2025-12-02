import { LivechatChannelKanbanRenderer } from "@im_livechat/views/livechat_channel_kanban/livechat_channel_kanban_renderer";

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";

const livechatChannelKanbanView = {
    ...kanbanView,
    Renderer: LivechatChannelKanbanRenderer,
};

registry.category("views").add("im_livechat.livechat_channel_kanban", livechatChannelKanbanView);
