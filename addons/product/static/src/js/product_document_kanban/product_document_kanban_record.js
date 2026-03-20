import { CANCEL_GLOBAL_CLICK, KanbanRecord } from "@web/views/kanban/kanban_record";
import { useService } from "@web/core/utils/hooks";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";

export class ProductDocumentKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        this.store = useService("mail.store");
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
            const attachment = this.store["ir.attachment"].insert({
                id: this.props.record.data.ir_attachment_id.id,
                name: this.props.record.data.name,
                mimetype: this.props.record.data.mimetype,
            });
            this.fileViewer.open(attachment);
            return;
        }
        return super.onGlobalClick(...arguments);
    }
}
