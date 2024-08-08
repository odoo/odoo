import { Component, useState, useEffect, markup } from "@odoo/owl";
import { ProgressBar } from "./file_upload_toast";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

export class UploadProgressManager extends Component {
    static template = "web.UploadProgressManager";
    static components = {
        ProgressBar,
    };

    static props = {
        files: { type: Object, optional: true },
        isVisible: { type: Boolean, optional: true },
        xhr: { type: Object, optional: true },
        close: { type: Function, optional: true },
        uploadInProgress: { type: Boolean, optional: true },
    };

    setup() {
        this.uploadService = useService("file_upload");
        this.dialogService = useService("dialog");
        this.state = useState(this.uploadService.fileProgressBar);
        this.abortUpload = this.abortUpload.bind(this);
        this.cancelAllUpload = this.cancelAllUpload.bind(this);
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
        if (this.props.files) {
            this.props.xhr.abort();
            delete this.props.files[targetFile.id];
            this.props.isVisible = false;
        } else {
            targetFile.abortFileUpload = false;
        }
    }

    cancelAllUpload() {
        if (this.state.uploadInProgress || this.props.uploadInProgress) {
            this.dialogService.add(ConfirmationDialog, {
                title: "Confirmation",
                confirmLabel: "Continue Uploads",
                cancelLabel: "Cancel Uploads",
                body: markup(
                    `<div class="text-dark h1 m-0 p-0">Cacel all uploads?</div>
                <div class="text-dark m-0 p-0">Your uploads are not complete. Would you like to cacnel all ongoing uploads?</div>`
                ),
                confirm: async () => {},
                cancel: () => {
                    this.state.xhr.abort();
                    this.state.files = {};
                    this.state.cancelAllUpload = true;
                    this.state.isVisible = false;
                },
            });
        } else {
            this.state.isVisible = false;
            if (this.props.files) {
                this.props.close(false);
            }
        }
    }
}
