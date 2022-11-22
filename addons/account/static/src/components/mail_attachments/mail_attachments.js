/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FileInput } from "@web/core/file_input/file_input";

const { Component, onWillUnmount } = owl;


export class MailAttachments extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.attachmentIdsToUnlink = new Set();

        onWillUnmount(this.onWillUnmount);
    }

    getValue(){
        return this.props.value || [];
    }

    getUrl(attachmentId) {
        return `/web/content/${attachmentId}?download=true`;
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
                garbage: true,
            });
        }
        this.props.update(this.getValue().concat(extraFiles));
    }

    onFileRemove(deleteId) {
        for(let item of this.getValue()){
            if(item.id == deleteId && item.garbage){
                this.attachmentIdsToUnlink.add(item.id);
            }
        }
        this.props.update(this.getValue().filtered((item) => !this.attachmentIdsToUnlink.contains(item.id)));
    }

    async onWillUnmount(){
        if(!this.props.record.resId){
            this.getValue().forEach((item) => {
                if(item.garbage){
                    this.attachmentIdsToUnlink.add(item.id);
                }
            });
        }
        if(this.attachmentIdsToUnlink.size > 0){
            await this.orm.unlink("ir.attachment", Array.from(this.attachmentIdsToUnlink));
        }
    }
}

MailAttachments.template = "account.mail_attachments";
MailAttachments.components = {FileInput};

registry.category("fields").add("mail_attachments", MailAttachments);
