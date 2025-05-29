import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/plugin_sets";
import { isEmpty } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { HtmlMailField, htmlMailField } from "../html_mail_field/html_mail_field";
import { MentionPlugin } from "./mention_plugin";
import { SIGNATURE_CLASS } from "@html_editor/main/signature_plugin";
import { fillEmpty } from "@html_editor/utils/dom";

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
                    this.editor.editable.querySelector(`.${SIGNATURE_CLASS}`)
                );
                const elContent = this.getNoSignatureElContent();
                // Temporarily Put the content in the DOM to be able to extract innerText newLines.
                this.editor.editable.after(elContent);
                // TODO: the following legacy regex may not have the desired effect as it
                // agglomerates multiple newLines together.
                const textValue = elContent.innerText.replace(/(\t|\n)+/g, "\n");
                elContent.remove();
                ev.detail.onSaveContent(textValue, emailAddSignature);
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
        this.editor.shared.signature.cleanSignatures({ rootClone: elContent });
        return elContent;
    }
}

export const htmlComposerMessageField = {
    ...htmlMailField,
    component: HtmlComposerMessageField,
};

registry.category("fields").add("html_composer_message", htmlComposerMessageField);
