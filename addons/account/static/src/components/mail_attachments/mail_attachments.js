import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FileInput } from "@web/core/file_input/file_input";
import { Component, onWillUnmount } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MailAttachments extends Component {
    static template = "account.mail_attachments";
    static components = { FileInput };
    static props = {...standardFieldProps};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.attachmentIdsToUnlink = new Set();

        onWillUnmount(this.onWillUnmount);
    }

    get attachments() {
        return this.props.record.data[this.props.name] || [];
    }

    onFileRemove(deleteId) {
        const newValue = [];

        for (let item of this.attachments) {
            if (item.id === deleteId) {
                if (item.placeholder || item.protect_from_deletion) {
                    const copyItem = Object.assign({ skip: true }, item);
                    newValue.push(copyItem);
                } else {
                    this.attachmentIdsToUnlink.add(item.id);
                }
            } else {
                newValue.push(item);
            }
        }

        this.props.record.update({ [this.props.name]: newValue });
    }

    async onWillUnmount() {
        // Unlink added attachments if the wizard is not saved.
        if (!this.props.record.resId) {
            this.attachments.forEach((item) => {
                if (item.manual) {
                    this.attachmentIdsToUnlink.add(item.id);
                }
            });
        }

        if (this.attachmentIdsToUnlink.size) {
            await this.orm.unlink("ir.attachment", Array.from(this.attachmentIdsToUnlink));
        }
    }
}

export const mailAttachments = {
    component: MailAttachments,
};

registry.category("fields").add("mail_attachments", mailAttachments);
