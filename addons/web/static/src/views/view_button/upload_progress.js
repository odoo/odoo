import { FileUploadProgressBar } from "@web/core/file_upload/file_upload_progress_bar";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { buttonUploads } from "./upload_button";

import { Component, xml } from "@odoo/owl";

/**
 * Shows the uploads of the upload buttons at the bottom of the screen, with
 * their progress, until the server has processed the files. They can be
 * cancelled.
 */
export class UploadProgress extends Component {
    // inline: this main component is also loaded by bundles without the view templates (public spreadsheet)
    static template = xml`
        <div t-if="this.uploads.length" class="o_upload_progress position-fixed bottom-0 end-0 d-flex flex-column gap-2 m-3">
            <div t-foreach="this.uploads" t-as="upload" t-key="upload.id"
                class="position-relative overflow-hidden d-flex align-items-center gap-2 rounded border bg-view shadow-lg py-2 ps-3 pe-4 small">
                <FileUploadProgressBar fileUpload="upload"/>
                <i class="oi oi-fw position-relative" data-icon="cloud_upload"/>
                <span class="position-relative text-truncate" t-out="this.getLabel(upload)"/>
            </div>
        </div>`;
    static components = { FileUploadProgressBar };

    get uploads() {
        return Object.values(buttonUploads);
    }

    getLabel(upload) {
        return upload.progress < 1
            ? _t("Uploading %s", upload.title)
            : _t("Processing %s", upload.title);
    }
}

registry.category("main_components").add("UploadProgress", { Component: UploadProgress });
