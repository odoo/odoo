import { registry } from "@web/core/registry";
import {
    many2ManyBinaryField,
    Many2ManyBinaryField
} from "@web/views/fields/many2many_binary/many2many_binary_field";

export class MailComposerAttachmentList extends Many2ManyBinaryField {
    static template = "mail.MailComposerAttachmentList";
}

export const mailComposerAttachmentList = {
    ...many2ManyBinaryField,
    component: MailComposerAttachmentList,
};

registry.category("fields").add("mail_composer_attachment_list", mailComposerAttachmentList);
