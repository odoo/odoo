/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { FileUploader } from "@web/views/fields/file_handler";
import { useService } from "@web/core/utils/hooks";

export class EdispatchUploader extends Component {
    static template = "l10n_tr_nilvera_edispatch.EdispatchUploader";
    static components = { FileUploader };
    static props = {
        slots: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.attachmentIdsToProcess = [];
        this.invalidAttachments = [];
    }

    async onFileUpload(file) {
        if (file.type != "text/xml") {
            this.invalidAttachments.push(file.name);
            return;
        }
        const file_data = {
            name: file.name,
            mimetype: file.type,
            raw: file.data,
        };
        const [attachmentId] = await this.orm.create("ir.attachment", [file_data]);
        this.attachmentIdsToProcess.push(attachmentId);
    }

    async onUploadComplete() {
        if (this.invalidAttachments.length !== 0) {
            this.notification.add(
                _t("The file(s): %s must be of type XML.", this.invalidAttachments.join(", ")),
                {
                    title: _t("Only XML files can be uploaded"),
                    type: "danger",
                }
            );
            this.invalidAttachments = [];
        }
        if (this.attachmentIdsToProcess.length === 0) {
            return;
        }
        try {
            const result = await this.orm.call("stock.picking", "l10n_tr_import_ereceipts", [
                "",
                this.attachmentIdsToProcess,
            ]);

            if (result) {
                if (result.action) {
                    this.notification.add(_t("e-Receipt(s) Imported Successfully"), {
                        type: "success",
                    });
                    this.action.doAction(result.action);
                }
                if (result.skipped_xmls) {
                    this.notification.add(
                        _t(
                            "Error occurred in reading following XML file(s): %s",
                            result.skipped_xmls.join(", ")
                        ),
                        { type: "danger", title: _t("e-Receipt(s) were not imported"), sticky: true }
                    );
                }
            }
        } catch (e) {
            this.notification.add(e.data.message, {
                title: _t("Something went wrong. Please try again."),
                type: "danger",
            });
        } finally {
            this.attachmentIdsToProcess = [];
        }
    }
}
