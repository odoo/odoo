import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/plugin_sets_others";
import { isEmpty } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { HtmlMailField, htmlMailField } from "../html_mail_field/html_mail_field";
import { SuggestionPlugin } from "@mail/core/common/plugins/suggestion_plugin";
import { ContentExpandablePlugin } from "./content_expandable_plugin";
import { SIGNATURE_CLASS } from "@html_editor/main/signature_plugin";

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
                const htmlValue = elContent.innerHTML;
                elContent.remove();
                ev.detail.onSaveContent(htmlValue, emailAddSignature);
            });
        }
    }

    getConfig() {
        const config = super.getConfig(...arguments);
        config.Plugins = [...config.Plugins, SuggestionPlugin];
        config.suggestionPLuginDependencies = {
            suggestionService: this.env.services["mail.suggestion"],
        };
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
        this.editor.shared.signature.cleanSignatures({ rootClone: elContent });
        return elContent;
    }
}

export const htmlComposerMessageField = {
    ...htmlMailField,
    additionalClasses: [...htmlMailField.additionalClasses, "ps-0"],
    component: HtmlComposerMessageField,
};

registry.category("fields").add("html_composer_message", htmlComposerMessageField);
