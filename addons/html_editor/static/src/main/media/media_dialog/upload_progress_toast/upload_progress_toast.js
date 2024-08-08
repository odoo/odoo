import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { UploadProgressEditorService } from "@web/core/file_upload/upload_progress_service";

export class UploadProgressToast extends Component {
    static template = "html_editor.UploadProgressToast";
    static components = {
        UploadProgressEditorService,
    };
    static props = {};

    setup() {
        this.uploadService = useService("upload");
        this.state = useState(this.uploadService.progressToast);
    }
}
