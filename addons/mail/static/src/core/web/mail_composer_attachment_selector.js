import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";

import { Component } from "@odoo/owl";
import { FileInput } from "@web/core/file_input/file_input";


export class MailComposerAttachmentSelector extends Component {
    static template = "mail.MailComposerAttachmentSelector";
    static components = { FileInput };
    static props = { ...standardFieldProps };

    setup() {
        this.notification = useService("notification");
        this.operations = useX2ManyCrud(() => {
            return this.props.record.data["attachment_ids"];
        }, true);
    }

    /** @param {Array[Object]} files */
    async onFileUploaded(files) {
        for (const file of files) {
            if (file.error) {
                return this.notification.add(file.error, {
                    title: _t("Uploading error"),
                    type: "danger",
                });
            }
            await this.operations.saveRecord([file.id]);
        }
    }
}

export const mailComposerAttachmentSelector = {
    component: MailComposerAttachmentSelector,
};

registry.category("fields").add("mail_composer_attachment_selector", mailComposerAttachmentSelector);
