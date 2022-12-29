/** @odoo-module **/

import { CANCEL_GLOBAL_CLICK, KanbanRecord } from "@web/views/kanban/kanban_record";
import { useService } from "@web/core/utils/hooks";
import { useAttachmentViewer } from "@mail/new/attachments/attachment_viewer_hook";

export class MrpDocumentsKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        this.attachmentService = useService("mail.attachment");
        this.attachmentViewer = useAttachmentViewer();
    }
    /**
     * @override
     *
     * Override to open the preview upon clicking the image, if compatible.
     */
    onGlobalClick(ev) {
        if (ev.target.closest(CANCEL_GLOBAL_CLICK) && !ev.target.classList.contains("o_mrp_download")) {
            return;
        }
        if (ev.target.classList.contains("o_mrp_download")) {
            window.location = `/web/content/mrp.document/${this.props.record.resId}/datas?download=true`;
            return;
        } else if (ev.target.closest(".o_kanban_previewer")) {
            const attachment = this.attachmentService.insert({
                id: this.props.record.data.ir_attachment_id[0],
                filename: this.props.record.data.name,
                name: this.props.record.data.name,
                mimetype: this.props.record.data.mimetype,
            });
            this.attachmentViewer.open(attachment)
            return;
        }
        return super.onGlobalClick(...arguments);
    }
}
