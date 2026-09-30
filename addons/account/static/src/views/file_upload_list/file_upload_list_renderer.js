import { _t } from '@web/core/l10n/translation';
import { ListRenderer } from "@web/views/list/list_renderer";
import { UploadDropZone } from "@account/components/upload_drop_zone/upload_drop_zone";
import { useState } from "@odoo/owl";
import { uploadFileFromData } from "../upload_file_from_data_hook";

export class FileUploadListRenderer extends ListRenderer {
    static template = "account.FileUploadListRenderer";
    static components = {
        ...ListRenderer.components,
        UploadDropZone,
    };

    setup() {
        super.setup();
        this.dropzoneState = useState({ visible: false });
        this.uploadFileFromData = uploadFileFromData();
        this.dropZoneTitle = _t("Drop and let the AI process your bills automatically.");
    }

    async onPaste(ev) {
        if (!ev.clipboardData?.items) {
            return;
        }
        ev.preventDefault();
        this.uploadFileFromData(ev.clipboardData);
    }

    onDragStart(ev) {
        if (ev.dataTransfer.types.includes("Files")) {
            this.dropzoneState.visible = true;
        }
    }
}
