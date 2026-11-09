import { KanbanRecord } from "@web/views/kanban/kanban_record";

export class LivechatChannelKanbanRecord extends KanbanRecord {
    getCardClasses() {
        const classes = super.getCardClasses();
        return this.props.record.data.available_operator_ids.count > 0
            ? `${classes} o-livechat-ChannelKanban-available`
            : classes;
    }
}
LivechatChannelKanbanRecord.menuTemplate = "im_livechat.KanbanRecordMenu";
