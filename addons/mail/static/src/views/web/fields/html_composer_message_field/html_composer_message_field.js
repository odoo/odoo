import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/backend/plugin_sets";
import { isEmpty } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { HtmlMailField, htmlMailField } from "../html_mail_field/html_mail_field";
import { MentionPlugin } from "./mention_plugin";
import { ContentExpandablePlugin } from "./content_expandable_plugin";
import { fillEmpty } from "@html_editor/utils/dom";
import { markup } from "@odoo/owl";

export class HtmlComposerMessageField extends HtmlMailField {
    setup() {
        super.setup();
        if (this.env.fullComposerBus) {
            useBus(this.env.fullComposerBus, "ACCIDENTAL_DISCARD", (ev) => {
                const elContent = this.getNoSignatureElContent();
                ev.detail.onAccidentalDiscard(isEmpty(elContent));
            });
            useBus(this.env.fullComposerBus, "SAVE_CONTENT", (ev) => {
                const emailAddSignature = Boolean(
                    this.editor.editable.querySelector(".o-signature-container")
                );
                const composerHtml = markup(this.getNoSignatureElContent().innerHTML);
                ev.detail.onSaveContent({ composerHtml, emailAddSignature });
            });
            useBus(this.env.fullComposerBus, "ATTACHMENT_REMOVED", (ev) => {
                const attachmentElements = this.editor.editable.querySelectorAll(
                    `[data-attachment-id="${ev.detail.id}"]`
                );
                attachmentElements.forEach((element) => {
                    const parent = element.parentElement;
                    element.remove();
                    fillEmpty(parent);
                });
                this.editor.shared.history.addStep();
            });
        }
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

    getNoSignatureElContent() {
        const elContent = this.editor.getElContent();
        for (const el of elContent.querySelectorAll(".o-signature-container")) {
            el.remove();
        }
        return elContent;
    }
}

export const htmlComposerMessageField = {
    ...htmlMailField,
    additionalClasses: [...htmlMailField.additionalClasses, "ps-0", "o_mail_composer_message"],
    component: HtmlComposerMessageField,
};

registry.category("fields").add("html_composer_message", htmlComposerMessageField);
