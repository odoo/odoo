// @ts-check

/** @module @web/components/file_upload/file_upload_progress_bar - Progress bar with cancel button for active file uploads */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/ui/dialog/confirmation_dialog";

export class FileUploadProgressBar extends Component {
    static template = "web.FileUploadProgressBar";
    static props = {
        fileUpload: { type: Object },
    };

    setup() {
        /** @type {import("@web/core").DialogService} */
        this.dialogService = useService("dialog");
    }

    /** Prompt user for confirmation, then abort the active XMLHttpRequest. */
    onCancel() {
        if (!this.props.fileUpload.xhr) {
            return;
        }
        this.dialogService.add(ConfirmationDialog, {
            body: _t(
                "Do you really want to cancel the upload of %s?",
                this.props.fileUpload.title,
            ),
            confirm: () => {
                this.props.fileUpload.xhr.abort();
            },
        });
    }
}
