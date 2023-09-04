/** @odoo-module **/

import { CANCEL_GLOBAL_CLICK, KanbanRecord } from "@web/views/kanban/kanban_record";
import { useService } from "@web/core/utils/hooks";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";

export class ProductDocumentKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        this.attachmentService = useService("mail.attachment");
        this.fileViewer = useFileViewer();
    }
    /**
     * @override
     *
     * Override to open the preview upon clicking the image, if compatible.
     */
    onGlobalClick(ev) {
        if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
            return;
        } else if (ev.target.closest(".o_kanban_previewer")) {
            const attachment = this.attachmentService.insert({
                id: this.props.record.data.ir_attachment_id[0],
                filename: this.props.record.data.name,
                name: this.props.record.data.name,
                mimetype: this.props.record.data.mimetype,
            });
            this.fileViewer.open(attachment)
            return;
        }
        return super.onGlobalClick(...arguments);
    }
}
