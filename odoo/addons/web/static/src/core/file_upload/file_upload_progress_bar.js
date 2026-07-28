/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "../utils/hooks";
import { ConfirmationDialog } from "../confirmation_dialog/confirmation_dialog";

import { Component } from "@odoo/owl";

export class FileUploadProgressBar extends Component {
    setup() {
        this.dialogService = useService("dialog");
    }

    onCancel() {
        if (!this.props.fileUpload.xhr) {
            return;
        }
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Do you really want to cancel the upload of %s?", this.props.fileUpload.title),
            confirm: () => {
                this.props.fileUpload.xhr.abort();
            },
        });
    }
}
FileUploadProgressBar.props = {
    fileUpload: { type: Object },
};
FileUploadProgressBar.template = "web.FileUploadProgressBar";
