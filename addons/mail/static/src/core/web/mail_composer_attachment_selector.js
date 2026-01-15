import { dataUrlToBlob } from "@mail/core/common/attachment_uploader_hook";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";

import { Component } from "@odoo/owl";
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
    }

    /** @param {Object} data */
    async onFileUploaded({ data, name, type }) {
        let resIds;
        if (this.props.record.resModel === "mail.scheduled.message") {
            resIds = [this.props.record.data.res_id.resId];
        } else {
            resIds = JSON.parse(this.props.record.data.res_ids);
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
}

export const mailComposerAttachmentSelector = {
    component: MailComposerAttachmentSelector,
};

registry
    .category("fields")
    .add("mail_composer_attachment_selector", mailComposerAttachmentSelector);
