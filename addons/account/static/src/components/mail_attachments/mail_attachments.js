/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FileInput } from "@web/core/file_input/file_input";
import { Component, onWillUnmount } from "@odoo/owl";

export class MailAttachments extends Component {
    static template = "account.mail_attachments";
    static components = { FileInput };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.attachmentIdsToUnlink = new Set();

        onWillUnmount(this.onWillUnmount);
    }

    getValue(){
        return this.props.record.data[this.props.name] || [];
    }

    getUrl(attachmentId) {
        return `/web/content/${attachmentId}?download=true`
    }

    getExtension(file) {
        return file.name.replace(/^.*\./, "");
    }

    onFileUploaded(files) {
        let extraFiles = [];
        for (const file of files) {
            if (file.error) {
                return this.notification.add(file.error, {
                    title: _t("Uploading error"),
                    type: "danger",
                });
            }

            extraFiles.push({
                id: file.id,
                name: file.filename,
                mimetype: file.mimetype,
                placeholder: false,
                manual: true,
            });
        }
        this.props.record.update({ [this.props.name]: this.getValue().concat(extraFiles) });
    }

    onFileRemove(deleteId) {
        const newValue = [];
        for (let item of this.getValue()) {
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

    async onWillUnmount(){
        // Unlink added attachments if the wizard is not saved.
        if(!this.props.record.resId){
            this.getValue().forEach((item) => {
                if(item.manual){
                    this.attachmentIdsToUnlink.add(item.id);
                }
            });
        }
        if(this.attachmentIdsToUnlink.size > 0){
            await this.orm.unlink("ir.attachment", Array.from(this.attachmentIdsToUnlink));
        }
    }
}

export const mailAttachments = {
    component: MailAttachments,
};

registry.category("fields").add("mail_attachments", mailAttachments);
