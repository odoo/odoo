import { LivechatChannelKanbanRecord } from "./livechat_channel_kanban_record";

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";

const livechatChannelKanbanView = {
    ...kanbanView,
    RecordLegacy: LivechatChannelKanbanRecord,
};

registry.category("views").add("im_livechat.livechat_channel_kanban", livechatChannelKanbanView);
