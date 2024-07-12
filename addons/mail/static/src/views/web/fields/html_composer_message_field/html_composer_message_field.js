import { registry } from "@web/core/registry";
import { HtmlMailField, htmlMailField } from "../html_mail_field/html_mail_field";

export class HtmlComposerMessageField extends HtmlMailField {
    getConfig() {
        const config = super.getConfig(...arguments);
        config.onAttachmentChange = (attachment) => {
            // This only needs to happen for the composer for now
            if (
                !(
                    this.props.record.fieldNames.includes("attachment_ids") &&
                    this.props.record.resModel === "mail.compose.message"
                )
            ) {
                return;
            }
            this.props.record.data.attachment_ids.linkTo(attachment.id, attachment);
        };
        return config;
    }
}

export const htmlComposerMessageField = {
    ...htmlMailField,
    component: HtmlComposerMessageField,
};

registry.category("fields").add("html_composer_message", htmlComposerMessageField);
