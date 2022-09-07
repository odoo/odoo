/** @odoo-module **/

import { useService } from "../utils/hooks";
import { sprintf } from "../utils/strings";
import { ConfirmationDialog } from "../confirmation_dialog/confirmation_dialog";

const { Component } = owl;

export class FileUploadProgressBar extends Component {
    setup() {
        this.dialogService = useService("dialog");
    }

    onCancel() {
        if (!this.props.fileUpload.xhr) {
            return;
        }
        this.dialogService.add(ConfirmationDialog, {
            body: sprintf(this.env._t("Do you really want to cancel the upload of %s?"), this.props.fileUpload.title),
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
