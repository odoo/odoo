import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    many2ManyBinaryField,
    Many2ManyBinaryField,
} from "@web/views/fields/many2many_binary/many2many_binary_field";
import { Many2XBinary } from "@web/views/fields/many2x_binary/many2x_binary_component";

export class MailComposerAttachmentBinary extends Many2XBinary {
    static template = "mail.MailComposerAttachmentBinary";
}

export class MailComposerAttachmentList extends Many2ManyBinaryField {
    static components = {
        ...Many2ManyBinaryField.components,
        Many2XBinary: MailComposerAttachmentBinary,
    };
    /** @override */
    setup() {
        super.setup();
        this.mailStore = useService("mail.store");
        this.attachmentUploadService = useService("mail.attachment_upload");
    }
    /**
     * @override
     * @param {integer} fileId
     */
    async onFileRemove(fileId) {
        super.onFileRemove(fileId);
        const attachment = this.mailStore["ir.attachment"].insert(fileId);
        await this.attachmentUploadService.unlink(attachment);
        this.env.fullComposerBus.trigger("ATTACHMENT_REMOVED", {
            id: attachment.id,
        });
    }
}

export const mailComposerAttachmentList = {
    ...many2ManyBinaryField,
    component: MailComposerAttachmentList,
};

registry.category("fields").add("mail_composer_attachment_list", mailComposerAttachmentList);
