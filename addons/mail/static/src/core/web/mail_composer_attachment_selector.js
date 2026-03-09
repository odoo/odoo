import { dataUrlToBlob } from "@mail/core/common/attachment_uploader_hook";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";

import { Component, onMounted } from "@odoo/owl";
import { FileUploader } from "@web/views/fields/file_handler";

export class MailComposerAttachmentSelector extends Component {
    static template = "mail.MailComposerAttachmentSelector";
    static components = { FileUploader };
    static props = { ...standardFieldProps };

    setup() {
        this.mailStore = useService("mail.store");
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.operations = useX2ManyCrud(() => {
            return this.props.record.data["attachment_ids"];
        }, true);
        // Turn attachments into links if needed when opening the composer.
        onMounted(() => {
            // The delay is required for the html-editor to be ready to receive the event that does the work.
            setTimeout(this.onAttachmentAdded.bind(this), 1000);
        });
    }

    /** @param {Object} data */
    async onFileUploaded({ data, name, type }) {
        let resIds;
        if (this.props.record.resModel === "mail.scheduled.message") {
            resIds = [this.props.record.data.res_id.resId];
        } else {
            // composer does not store res_ids past a certain limit, assume active_ids is used
            resIds = this.props.record.data.res_ids
                ? JSON.parse(this.props.record.data.res_ids)
                : this.props.record.context.active_ids;
        }
        const thread = await this.mailStore.Thread.insert({
            model: this.props.record.data.model,
            id: resIds[0],
        });
        const file = new File([dataUrlToBlob(data, type)], name, { type });
        const attachment = await this.attachmentUploadService.upload(thread, thread.composer, file);
        if (attachment) {
            await this.operations.saveRecord([attachment.id]);
        }
    }

    onAttachmentAdded() {
        this.env.fullComposerBus?.trigger("ATTACHMENT_ADDED", {
            attachments: this.props.record.data.attachment_ids.records,
        });
    }
}

export const mailComposerAttachmentSelector = {
    component: MailComposerAttachmentSelector,
    relatedFields: () => {
        return [
            { name: "file_size", type: "integer", readOnly: true },
            { name: "id", type: "integer", readonly: true },
        ];
    },
};

registry
    .category("fields")
    .add("mail_composer_attachment_selector", mailComposerAttachmentSelector);
