import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FileInput } from "@web/core/file_input/file_input";
import { FileUploader } from "@web/views/fields/file_handler";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MailAttachments extends Component {
    static template = "mail.MailComposerAttachmentSelector";
    static components = { FileInput, FileUploader };
    static props = {...standardFieldProps};

    setup() {
        this.notification = useService("notification");
    }

    get attachments() {
        return this.props.record.data[this.props.name] || [];
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
        this.props.record.update({ [this.props.name]: this.attachments.concat(extraFiles) });
    }
}

export const mailAttachments = {
    component: MailAttachments,
};

registry.category("fields").add("mail_attachments_selector", mailAttachments);
