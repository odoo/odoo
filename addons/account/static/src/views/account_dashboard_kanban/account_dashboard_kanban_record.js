import { onWillDestroy, usePlugin } from "@odoo/owl";
import { DropzonePlugin } from "@web/core/dropzone/dropzone_plugin";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { UploadDropzonePlugin } from "@web/webclient/upload_dropzone_plugin";

export class DashboardKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        const uploadDropzone = usePlugin(UploadDropzonePlugin);
        const getUploadButton = () => this.rootRef()?.querySelector("[type='upload']");
        const removeDropzone = usePlugin(DropzonePlugin).add(this.rootRef, {
            label: this.props.record.data.name,
            onDrop: (files) => uploadDropzone.uploadWithButton(getUploadButton(), files),
            isEnabled: () => Boolean(getUploadButton()),
        });
        onWillDestroy(removeDropzone);
    }
}
