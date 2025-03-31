import { _t } from "@web/core/l10n/translation";
import { FileUploadProgressBar } from "./file_upload_progress_bar";

import { Component } from "@odoo/owl";

export class FileUploadProgressRecord extends Component {
    static template = "";
    static components = {
        FileUploadProgressBar,
    };
    static props = {
        fileUpload: Object,
        selector: { type: String, optional: true },
    };
    getProgressTexts() {
        const fileUpload = this.props.fileUpload;
        const percent = Math.round(fileUpload.progress * 100);
        if (percent === 100) {
            return {
                left: _t("Processing..."),
                right: "",
            };
        } else {
            const mbLoaded = Math.round(fileUpload.loaded / 1000000);
            const mbTotal = Math.round(fileUpload.total / 1000000);
            return {
                left: _t("Uploading... (%s%)", percent),
                right: _t("(%(mbLoaded)s/%(mbTotal)sMB)", { mbLoaded, mbTotal }),
            };
        }
    }
}

export class FileUploadProgressKanbanRecord extends FileUploadProgressRecord {
    static template = "web.FileUploadProgressKanbanRecord";
}

export class FileUploadProgressDataRow extends FileUploadProgressRecord {
    static template = "web.FileUploadProgressDataRow";
}
