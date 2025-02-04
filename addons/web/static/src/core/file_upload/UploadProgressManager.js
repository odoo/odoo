import { Component } from "@odoo/owl";
import { ProgressBar } from "./file_upload_toast";

export class UploadProgressManager extends Component {
    static template = "web.UploadProgressManager";
    static components = { ProgressBar };

    static props = {
        files: { type: Object, optional: false },
        close: { type: Function, optional: true },
        uploadInProgress: { type: Boolean, optional: true },
        abortUpload: { type: Function, optional: true },
        cancelAllUpload: { type: Function, optional: true },
        totalFilesCount: { type: Number, optional: true },
        multipleFiles: { type: Boolean, optional: true },
    };
}
