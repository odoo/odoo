import { useService } from "@web/core/utils/hooks";

import { Component, markup } from "@odoo/owl";

export const AbstractDocumentFileUploader = (T = Component)  => class AbstractDocumentFileUploader extends T {

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.attachmentIdsToProcess = [];
        this.extraContext = this.getExtraContext();
    }

    // To pass extra context while creating record
    getExtraContext() {
        return {};
    }

    async onFileUploaded(file) {
        const att_data = {
            name: file.name,
            mimetype: file.type,
            raw: file.data,
        };
        const [att_id] = await this.orm.create("ir.attachment", [att_data], {context: this.cleanContext});
        this.attachmentIdsToProcess.push(att_id);
    }

    // To define specific resModal from another model
    getResModel() {
        throw new Error("You should implement this method !");
    }

    get onUploadCompleteContext() {
        return {};
    }

    get cleanContext() {
        return {};
    }

    async onUploadComplete() {
        const resModal = this.getResModel();
        let action;
        try {
            action = await this.orm.call(
                resModal,
                "create_document_from_attachment",
                ["", this.attachmentIdsToProcess],
                { context: this.onUploadCompleteContext  }
            );
        } finally {
            // ensures attachments are cleared on success as well as on error
            this.attachmentIdsToProcess = [];
        }
        if (action.context && action.context.notifications) {
            for (const [file, msg] of Object.entries(action.context.notifications)) {
                this.notification.add(msg, {
                    title: file,
                    type: "info",
                    sticky: true,
                });
            }
            delete action.context.notifications;
        }
        if (action.help?.length) {
            action.help = markup(action.help);
        }
        this.action.doAction(action);
    }
}
