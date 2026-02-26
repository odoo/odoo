import { DYNAMIC_FIELD_PLUGINS } from "@html_editor/backend/dynamic_field/dynamic_field_plugin";
import { FilePlugin } from "@html_editor/main/media/file_plugin";
import { isEmpty } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { HtmlMailField, htmlMailField } from "../html_mail_field/html_mail_field";
import { MailFullComposerSuggestionPlugin } from "./mail_full_composer_suggestion_plugin";
import { ContentExpandablePlugin } from "./content_expandable_plugin";
import { DisableBannerCommandsPlugin } from "./disable_banner_commands_plugin";
import { fillEmpty } from "@html_editor/utils/dom";
import { markup } from "@odoo/owl";

export class HtmlComposerMessageField extends HtmlMailField {
    setup() {
        super.setup();
        const notification = useService("notification");
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
            useBus(this.env.fullComposerBus, "ADD_INLINE_ATTACHMENTS", async (ev) => {
                const filePlugin = this.editor.plugins.find(
                    (p) => p.constructor.id === FilePlugin.id
                );
                if (!filePlugin) {
                    return;
                }
                const attachments = ev.detail.attachments.map((a) => a.data);
                // Filter out already added attachments
                const filteredAttachments = attachments.filter(
                    (a) =>
                        !this.editor.editable.querySelectorAll(`[data-attachment-id="${a.id}"]`)
                            .length
                );
                if (!filteredAttachments.length) {
                    return;
                }
                const attachmentContainer = this.editor.editable.querySelector(
                    ".o-attachments-container"
                );
                if (!attachmentContainer) {
                    const newAttachmentContainer = document.createElement("div");
                    newAttachmentContainer.classList.add(
                        "o-attachments-container",
                        "o-contenteditable-false"
                    );
                    newAttachmentContainer.contentEditable = false;
                    attachments.forEach((a) =>
                        newAttachmentContainer.appendChild(filePlugin.renderDownloadBox(a))
                    );
                    const signature = this.editor.editable.querySelector(".o-signature-container");
                    if (signature) {
                        signature.before(newAttachmentContainer);
                    } else {
                        this.editor.editable.firstChild.before(newAttachmentContainer);
                    }
                } else {
                    filteredAttachments.forEach((a) =>
                        attachmentContainer.appendChild(filePlugin.renderDownloadBox(a))
                    );
                }
                this.editor.shared.history.addStep();
                notification.add(ev.detail.message, { type: "info" });
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
        config.Plugins = [
            ...config.Plugins.filter((plugin) => !["video"].includes(plugin.id)),
            DisableBannerCommandsPlugin,
            MailFullComposerSuggestionPlugin,
        ];
        if (this.props.record.data.composition_comment_option === "reply_all") {
            config.Plugins.push(ContentExpandablePlugin);
        }
        if (!this.props.record.data.composition_batch) {
            config.Plugins = config.Plugins.filter(
                (plugin) => !DYNAMIC_FIELD_PLUGINS.includes(plugin)
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
        config.thread = this.env.services["mail.store"]?.["mail.thread"].get({
            model: this.props.record.data.model,
            id: JSON.parse(this.props.record.data.res_ids || "[]")[0],
        });
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
