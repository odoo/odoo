/** @odoo-module **/

import { FileUploadProgressBar } from "./file_upload_progress_bar";

import { Component } from "@odoo/owl";

export class FileUploadProgressRecord extends Component {
    getProgressTexts() {
        const fileUpload = this.props.fileUpload;
        const percent = Math.round(fileUpload.progress * 100);
        if (percent === 100) {
            return {
                left: this.env._t("Processing..."),
                right: "",
            };
        } else {
            const mbLoaded = Math.round(fileUpload.loaded / 1000000);
            const mbTotal = Math.round(fileUpload.total / 1000000);
            return {
                left: this.env._t("Uploading... (%s%)", percent),
                right: this.env._t("(%s/%sMB)", mbLoaded, mbTotal),
            };
        }
    }
}
FileUploadProgressRecord.components = {
    FileUploadProgressBar,
};

export class FileUploadProgressKanbanRecord extends FileUploadProgressRecord {}
FileUploadProgressKanbanRecord.template = "web.FileUploadProgressKanbanRecord";

export class FileUploadProgressDataRow extends FileUploadProgressRecord {}
FileUploadProgressDataRow.template = "web.FileUploadProgressDataRow";
