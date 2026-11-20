import { dataUrlToBlob } from "@mail/core/common/attachment_uploader_hook";
import { registry } from "@web/core/registry";
import { Record } from "@web/model/relational_model/record";

import { Component, types, useProps } from "@odoo/owl";
import { FileUploader } from "@web/views/fields/file_handler";

import { useMailComposerAttachmentsUploader } from "./mail_composer_attachment_hook";

export class MailComposerAttachmentSelector extends Component {
    static template = "mail.MailComposerAttachmentSelector";
    static components = { FileUploader };

    setup() {
        this.props = useProps({ record: types.instanceOf(Record) });
        this.doUpload = useMailComposerAttachmentsUploader();
    }

    /** @param {Object} data */
    async onFileUploaded({ data, name, type }) {
        await this.doUpload([new File([dataUrlToBlob(data, type)], name, { type })]);
    }
}

export const mailComposerAttachmentSelector = {
    component: MailComposerAttachmentSelector,
};

registry
    .category("fields")
    .add("mail_composer_attachment_selector", mailComposerAttachmentSelector);
