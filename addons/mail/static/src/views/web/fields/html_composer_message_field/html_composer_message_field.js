import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/plugin_sets";
import { registry } from "@web/core/registry";
import { HtmlMailField, htmlMailField } from "../html_mail_field/html_mail_field";
import { MentionPlugin } from "./mention_plugin";
import { ContentExpandablePlugin } from "./content_expandable_plugin";

import { onMounted } from "@odoo/owl";

export class HtmlComposerMessageField extends HtmlMailField {
    setup() {
        super.setup();
        onMounted(() => {
            this.editor.shared.selection.setSelection({
                anchorNode: this.editor.editable,
                anchorOffset: 0,
            });
        });
    }

    getConfig() {
        const config = super.getConfig(...arguments);
        config.Plugins = [...config.Plugins, MentionPlugin];
        if (this.props.record.data.composition_comment_option === "reply_all") {
            config.Plugins.push(ContentExpandablePlugin);
        }
        if (!this.props.record.data.composition_batch) {
            config.Plugins = config.Plugins.filter(
                (plugin) => !DYNAMIC_PLACEHOLDER_PLUGINS.includes(plugin)
            );
        }
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
    additionalClasses: [...htmlMailField.additionalClasses, "ps-0"],
    component: HtmlComposerMessageField,
};

registry.category("fields").add("html_composer_message", htmlComposerMessageField);
