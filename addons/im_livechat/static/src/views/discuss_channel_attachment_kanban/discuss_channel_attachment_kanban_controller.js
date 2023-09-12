/* @odoo-module */

import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";

export class DiscussChannelAttachmentKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
        this.fileViewer = useFileViewer();
        this.store = useService("mail.store");
    }

    async openRecord(record) {
        const attachment = this.store.Attachment.insert({
            id: record.data.id,
            filename: record.data.name,
            name: record.data.name,
            mimetype: record.data.mimetype,
        });
        this.fileViewer.open(attachment);
    }
}
