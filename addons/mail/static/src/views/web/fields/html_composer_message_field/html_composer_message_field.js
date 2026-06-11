import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/plugin_sets";
import { isEmpty } from "@html_editor/utils/dom_info";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { HtmlMailField, htmlMailField } from "../html_mail_field/html_mail_field";
import { MentionPlugin } from "./mention_plugin";
import { SIGNATURE_CLASS } from "@html_editor/main/signature_plugin";
import { fillEmpty } from "@html_editor/utils/dom";

export class HtmlComposerMessageField extends HtmlMailField {
    setup() {
        super.setup();
        const notification = useService("notification");
        const uploadService = useService("uploadLocalFiles");
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
            useBus(this.env.fullComposerBus, "ATTACHMENT_ADDED", async (ev) => {
                // Attachments added with the html editor directly should not be taken into account
                const allAttachmentIdsNode = Array.from(
                    this.editor.editable.querySelectorAll("[data-attachment-id]")
                );
                const outSideAttachmentIds = allAttachmentIdsNode
                    .filter((el) => el.closest(".o-attachments-container") === null)
                    .map((el) => Number(el.getAttribute("data-attachment-id")));
                const attachments = ev.detail.attachments
                    .map((a) => a.data)
                    .filter((a) => !outSideAttachmentIds.includes(a.id));
                // Filter out already added attachments
                const allAttachmentIds = allAttachmentIdsNode.map((el) =>
                    Number(el.getAttribute("data-attachment-id"))
                );
                const filteredAttachments = attachments.filter(
                    (a) => !allAttachmentIds.includes(a.id)
                );
                if (!filteredAttachments.length) {
                    return;
                }
                const maxEmailSize = 10;
                const totalSize = attachments
                    .map((a) => a.file_size)
                    .reduce((acc, current) => acc + current, 0);
                // Approximate the server-side mail size estimation (mail_mail._estimate_email_size)
                const emailOverhead = 100 * 1024;
                if (totalSize + emailOverhead <= maxEmailSize * 1024 * 1024) {
                    return;
                }
                const newAttachmentContainer = renderToElement("mail.mail_attachment_links", {
                    attachments: attachments.map((attachment) => ({
                        ...attachment,
                        url: uploadService.getURL(attachment, {
                            download: true,
                            unique: true,
                            accessToken: true,
                        }),
                    })),
                });
                const attachmentContainer = this.editor.editable.querySelector(
                    ".o-attachments-container"
                );
                if (!attachmentContainer) {
                    const signature = this.editor.editable.querySelector(".o-signature-container");
                    if (signature) {
                        signature.before(newAttachmentContainer);
                    } else {
                        this.editor.editable.firstChild.before(newAttachmentContainer);
                    }
                } else {
                    attachmentContainer.replaceWith(newAttachmentContainer);
                }
                this.editor.shared.history.addStep();
                notification.add(
                    _t(
                        "Your attachments exceed %(maxSizeInMB)sMB and will be sent as secure links to ensure they reach your recipients",
                        { maxSizeInMB: Math.round(maxEmailSize) }
                    ),
                    { type: "info" }
                );
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
        config.thread = this.env.services["mail.store"]?.Thread.get({
            model: this.props.record.data.model,
            id: JSON.parse(this.props.record.data.res_ids || "[]")[0],
        });
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
