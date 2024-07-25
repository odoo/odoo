import { ListRenderer } from "@web/views/list/list_renderer";
import { UploadDropZone } from "@account/components/upload_drop_zone/upload_drop_zone";
import { useState } from "@odoo/owl";

export class FileUploadListRenderer extends ListRenderer {
    static template = "account.FileUploadListRenderer";
    static components = {
        ...ListRenderer.components,
        UploadDropZone,
    };

    setup() {
        super.setup();
        this.dropzoneState = useState({ visible: false });
    }
}
