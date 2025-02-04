import { Component, useState, useEffect, markup } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { fileProgressBar } from "./upload_utils";
import { UploadProgressManager } from "./UploadProgressManager";

export class UploadProgressService extends Component {
    static template = "web.UploadProgressService";
    static components = { UploadProgressManager };
    static props = {};

    setup() {
        this.uploadService = useService("file_upload");
        this.dialogService = useService("dialog");
        this.state = useState(fileProgressBar);
        useEffect(() => {
            const handleBeforeUnload = (event) => {
                if (this.state.uploadInProgress) {
                    event.preventDefault();
                    event.returnValue = "";
                }
            };
            window.addEventListener("beforeunload", handleBeforeUnload);
            // Cleanup function to remove the event listener
            return () => {
                window.removeEventListener("beforeunload", handleBeforeUnload);
            };
        });
    }

    abortUpload(targetFile) {
        if (this.state.xhr && !targetFile.abortFileUpload) {
            delete this.state.files[targetFile.id];
            this.state.xhr.abort(); // Abort the upload
            targetFile.abortFileUpload = true;
            if (Object.keys(this.state.files).length === 0) {
                this.state.isVisible = false;
            }
        }
    }

    cancelAllUpload() {
        if (this.state.uploadInProgress) {
            this.dialogService.add(ConfirmationDialog, {
                title: "Confirmation",
                confirmLabel: "Continue Uploads",
                cancelLabel: "Cancel Uploads",
                body: markup(
                    `<div class="text-dark h1 m-0 p-0">Cancel all uploads?</div>
                <div class="text-dark m-0 p-0">Your uploads are not complete. Would you like to cancel all ongoing uploads?</div>`
                ),
                confirm: async () => {},
                cancel: () => {
                    this.state.xhr.abort();
                    this.state.files = {};
                    if (!this.state.multipleFiles) {
                        this.state.cancelAllUpload = true;
                    }
                    this.state.isVisible = false;
                },
                dismiss: () => false,
            });
        }
    }
}

export class UploadProgressEditorService extends Component {
    static template = "web.UploadProgressEditorService";
    static components = { UploadProgressManager };
    static props = {
        files: { type: Object, optional: true },
        isVisible: { type: Boolean, optional: true },
        xhr: { type: Object, optional: true },
        close: { type: Function, optional: true },
        uploadInProgress: { type: Boolean, optional: true },
    };

    abortUpload(targetFile) {
        this.props.xhr.abort();
        delete this.props.files[targetFile.id];
        this.props.close(false);
    }

    cancelAllUpload() {
        this.props.close(false);
    }
}
