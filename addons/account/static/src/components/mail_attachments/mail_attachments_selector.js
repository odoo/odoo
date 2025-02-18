import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { dataUrlToBlob } from "@mail/core/common/attachment_uploader_hook";

export class MailAttachments extends Component {
    static template = "mail.MailComposerAttachmentSelector";
    static components = { FileUploader };
    static props = {...standardFieldProps};

    setup() {
        this.mailStore = useService("mail.store");
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.operations = useX2ManyCrud(() => {
            return this.props.record.data["attachment_ids"];
        }, true);
    }

    get attachments() {
        return this.props.record.data[this.props.name] || [];
    }

    async onFileUploaded({ name, data, type }) {
        const resIds = JSON.parse(this.props.record.data.res_ids);
        const thread = await this.mailStore.Thread.insert({
            model: this.props.record.data.model,
            id: resIds[0],
        });

        const file = new File([dataUrlToBlob(data, type)], name, { type });
        const attachment = await this.attachmentUploadService.upload(thread, thread.composer, file);

        let fileDict = {
            id: attachment.id,
            name: attachment.name,
            mimetype: attachment.mimetype,
            placeholder: false,
            manual: true,
        };
        this.props.record.update({ [this.props.name]: this.attachments.concat([fileDict]) });
    }
}

export const mailAttachments = {
    component: MailAttachments,
};

registry.category("fields").add("mail_attachments_selector", mailAttachments);
