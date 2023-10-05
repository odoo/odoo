/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRef } from "@odoo/owl";

export class ProductDocumentKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.uploadFileInputRef = useRef("uploadFileInput");
        this.fileUploadService = useService("file_upload");
        useBus(
            this.fileUploadService.bus,
            "FILE_UPLOAD_LOADED",
            async () => {
                await this.model.root.load();
            },
        );
    }

    async onFileInputChange(ev) {
        if (!ev.target.files.length) {
            return;
        }
        await this.fileUploadService.upload(
            "/product/document/upload",
            ev.target.files,
            {
                buildFormData: (formData) => {
                    formData.append("res_model", this.props.context.active_model);
                    formData.append("res_id", this.props.context.active_id);
                },
            },
        );
        // Reset the file input's value so that the same file may be uploaded twice.
        ev.target.value = "";
    }
}
