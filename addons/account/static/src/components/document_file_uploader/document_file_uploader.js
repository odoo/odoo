import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { Component, markup } from "@odoo/owl";

export class DocumentFileUploader extends Component {
    static template = "account.DocumentFileUploader";
    static components = {
        FileUploader,
    };
    static props = {
        ...standardWidgetProps,
        record: { type: Object, optional: true },
        slots: { type: Object, optional: true },
        resModel: { type: String, optional: true },
    };

    setup() {
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
            datas: file.data,
        };
        // clean the context to ensure the `create` call doesn't fail from unknown `default_*` context
        const cleanContext = Object.fromEntries(Object.entries(this.env.searchModel.context).filter(([key]) => !key.startsWith('default_')));
        const [att_id] = await this.orm.create("ir.attachment", [att_data], {context: cleanContext});
        this.attachmentIdsToProcess.push(att_id);
    }

    // To define specific resModal from another model
    getResModel() {
        return this.props.resModel;
    }

    async onUploadComplete() {
        const resModal = this.getResModel();
        let action;
        try {
            action = await this.orm.call(
                resModal,
                "create_document_from_attachment",
                ["", this.attachmentIdsToProcess],
                { context: { ...this.extraContext, ...this.env.searchModel.context } }
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
