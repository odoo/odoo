// @ts-check

/** @module @web/components/file_upload/file_upload_progress_record - Per-record file upload overlay showing percentage and MB progress */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

import { FileUploadProgressBar } from "./file_upload_progress_bar";
export class FileUploadProgressRecord extends Component {
    static template = "";
    static components = {
        FileUploadProgressBar,
    };
    static props = {
        fileUpload: Object,
        selector: { type: String, optional: true },
    };
    /**
     * Compute progress display texts for the upload overlay.
     * @returns {{ left: string, right: string }} left label and right MB counter
     */
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
                right: _t("(%(mbLoaded)s/%(mbTotal)sMB)", {
                    mbLoaded,
                    mbTotal,
                }),
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
