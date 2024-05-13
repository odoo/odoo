import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { LivechatChannelKanbanRecord } from "./livechat_channel_kanban_record";

export class LivechatChannelKanbanRenderer extends KanbanRenderer {
    get kanbanRecordComponent() {
        return LivechatChannelKanbanRecord;
    }
}
