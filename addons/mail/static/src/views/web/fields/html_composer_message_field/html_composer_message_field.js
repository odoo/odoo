import { htmlField, HtmlField } from "@html_editor/fields/html_field";
import { registry } from "@web/core/registry";

// @todo @phoenix should extends HtmlMailField
export class HtmlComposerMessageField extends HtmlField {
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
    ...htmlField,
    component: HtmlComposerMessageField,
    additionalClasses: ["o_field_html"],
};

registry.category("fields").add("html_composer_message", htmlComposerMessageField);
