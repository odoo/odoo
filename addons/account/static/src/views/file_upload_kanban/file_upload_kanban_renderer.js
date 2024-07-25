import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { UploadDropZone } from "@account/components/upload_drop_zone/upload_drop_zone";
import { useState } from "@odoo/owl";

export class FileUploadKanbanRenderer extends KanbanRenderer {
    static template = "account.FileUploadKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        UploadDropZone,
    };

    setup() {
        super.setup();
        this.dropzoneState = useState({ visible: false });
    }
}
