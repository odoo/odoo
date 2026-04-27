import { browser } from "@web/core/browser/browser";
import { ErrorDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { CopyButton } from "@web/core/copy_button/copy_button";

import { patch } from "@web/core/utils/patch";
import { onWillStart } from "@odoo/owl";

patch(ErrorDialog.components, {
    CopyButton,
});

patch(ErrorDialog.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.fileUpload = useService("file_upload");
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.state.tracebackUrl = null;
        this.state.processed = false;
        this.canUploadTraceback = false;
        useBus(this.fileUpload.bus, "FILE_UPLOAD_LOADED", async (ev) => {
            if (ev.detail.upload.xhr.status === 200 && this.state.processed) {
                const response = JSON.parse(ev.detail.upload.xhr.response);
                if (response.length === 1) {
                    this.state.tracebackUrl = response[0];
                    setTimeout(async () => {
                        await browser.navigator.clipboard.writeText(response[0]);
                        this.notification.add(_t("The document URL has been copied to your clipboard."), {
                            type: "success"
                        });
                    });
                }
            }
        });
        onWillStart(async () => {
            try {
                this.canUploadTraceback = await this.orm.call(
                    "documents.document",
                    "can_upload_traceback"
                );
            } catch {
                this.canUploadTraceback = false;
            }
        });
    },
    shareTraceback() {
        if (!this.state.processed) {
            this.state.processed = true;
            const file = new File(
                [
                    `${this.props.name}\n\n${this.props.message}\n\n${this.contextDetails}\n\n${
                        this.traceback || this.props.traceback
                    }`,
                ],
                `${this.constructor.title} - ${luxon.DateTime.local().toFormat(
                    "yyyy-MM-dd HH:mm:ss"
                )}.txt`,
                { type: "text/plain" }
            );
            this.fileUpload.upload("/documents/upload_traceback", [file], {});
        }
    },
});
