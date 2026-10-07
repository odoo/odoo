import { useCustomDropzone } from "@web/core/dropzone/dropzone_hook";
import { UploadDropzone } from "@web/core/dropzone/upload_dropzone";
import { pick } from "@web/core/utils/objects";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { useViewButtonHandler } from "@web/views/view_button/view_button_hook";

export class DashboardKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        const handleViewButton = useViewButtonHandler();
        useCustomDropzone(this.rootRef, UploadDropzone, {
            label: this.props.record.data.name,
            onDrop: (files) =>
                handleViewButton({
                    clickParams: { type: "upload", name: "create_document_from_attachment" },
                    getResParams: () =>
                        pick(this.props.record, "context", "evalContext", "resModel", "resId", "resIds"),
                    files,
                }),
        });
    }
}
