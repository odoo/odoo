import { dataUrlToBlob } from "@mail/core/common/attachment_uploader_hook";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { Record } from "@web/model/relational_model/record";

import { Component, types, useProps } from "@odoo/owl";
import { FileUploader } from "@web/views/fields/file_handler";

import { useMailComposerAttachmentsUploader } from "./mail_composer_attachment_hook";

export class MailComposerAttachmentSelector extends Component {
    static template = "mail.MailComposerAttachmentSelector";
    static components = { FileUploader };

    setup() {
        this.props = useProps({ record: types.instanceOf(Record) });
        this.mailStore = useService("mail.store");
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.operations = useX2ManyCrud(() => this.props.record.data["attachment_ids"], true);
        this.doUpload = useMailComposerAttachmentsUploader();
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
<<<<<<< 432cfc29e68712037ab536d0c9c57a03b9ac271e
        const thread = await this.mailStore["mail.thread"].insert({
            model: this.props.record.data.model || this.props.record.context.active_model,
            id: resIds[0],
        });
        const file = new File([dataUrlToBlob(data, type)], name, { type });
        const syncAttachmentsToThreadComposer =
            this.props.record.context.sync_attachments_to_thread_composer;
        let composer = syncAttachmentsToThreadComposer ? thread.composer : undefined;
        // Use an isolated composer object instead of thread.composer to
        // avoid pushing into the main thread's composer.attachments list,
        // which is observed by the chatter.
        if (this.props.record.resModel === "mail.scheduled.message") {
            composer = { attachments: [] };
        }
        const attachment = await this.attachmentUploadService.upload(thread, composer, file);
        if (attachment) {
            await this.operations.saveRecord([attachment.id]);
        }
||||||| c574f2dc044ebc8b0f42c27a0d0acff0561aad73
        const thread = await this.mailStore["mail.thread"].insert({
            model: this.props.record.data.model || this.props.record.context.active_model,
            id: resIds[0],
        });
        const file = new File([dataUrlToBlob(data, type)], name, { type });
        const isThreadComposer = this.props.record.context.is_thread_composer;
        let composer = isThreadComposer ? thread.composer : undefined;
        // Use an isolated composer object instead of thread.composer to
        // avoid pushing into the main thread's composer.attachments list,
        // which is observed by the chatter.
        if (this.props.record.resModel === "mail.scheduled.message") {
            composer = { attachments: [] };
        }
        const attachment = await this.attachmentUploadService.upload(thread, composer, file);
        if (attachment) {
            await this.operations.saveRecord([attachment.id]);
        }
=======

        const uploadFile = async () => {
            const thread = await this.mailStore["mail.thread"].insert({
                model: this.props.record.data.model || this.props.record.context.active_model,
                id: resIds[0],
            });
            const file = new File([dataUrlToBlob(data, type)], name, { type });
            const isThreadComposer = this.props.record.context.is_thread_composer;
            let composer = isThreadComposer ? thread.composer : undefined;
            // Use an isolated composer object instead of thread.composer to
            // avoid pushing into the main thread's composer.attachments list,
            // which is observed by the chatter.
            if (this.props.record.resModel === "mail.scheduled.message") {
                composer = { attachments: [] };
            }
            const attachment = await this.attachmentUploadService.upload(thread, composer, file);
            if (attachment) {
                await this.operations.saveRecord([attachment.id]);
            }
        };
        await this.doUpload(uploadFile());
>>>>>>> 2f7fceba79035f4107dc7c2670242d29023f1370
    }
}

export const mailComposerAttachmentSelector = {
    component: MailComposerAttachmentSelector,
};

registry
    .category("fields")
    .add("mail_composer_attachment_selector", mailComposerAttachmentSelector);
