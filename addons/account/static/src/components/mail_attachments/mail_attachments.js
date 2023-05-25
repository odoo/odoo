/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FileInput } from "@web/core/file_input/file_input";

const { Component, onWillUnmount } = owl;


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
                    title: this.env._t("Uploading error"),
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
        for(let item of this.getValue()){
            if(item.id == deleteId && !item.placeholder){
                this.attachmentIdsToUnlink.add(item.id);
            }
        }
        this.props.record.update({ [this.props.name]: this.getValue().filter((item) => !this.attachmentIdsToUnlink.has(item.id)) });
    }

    async onWillUnmount(){
        // Unlink added attachments if the wizard is not saved.
        if(!this.props.record.data.id){
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
