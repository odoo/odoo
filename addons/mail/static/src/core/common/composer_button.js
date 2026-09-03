import { Component, useState } from "@odoo/owl";
import { useService } from '@web/core/utils/hooks';
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class ComposerSendButton extends Component {
    static template = "mail.Composer.sendButtonWidget";
    static props = {
        ...standardWidgetProps,
        text: { type: String },
    };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        const attachmentUploadService = useService("mail.attachment_upload");
        this.uploadingAttachments = useState(attachmentUploadService.uploadingAttachmentIds)
    }

    onClick() {
        if (this.uploadingAttachments.size > 0) {
            this.notification.add(_t("Please wait while the file is uploading."), {
                type: "warning",
            });
            return;
        }
        this.action.doAction("action_send_mail")
    }
}

export const composerSendButtonWidget = {
    component: ComposerSendButton,
    extractProps: ({ attrs }) => {
        return {
            text: attrs.text,
        };
    },
};

registry.category("view_widgets").add("composer_send_button", composerSendButtonWidget);
