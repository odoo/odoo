import { DYNAMIC_FIELD_PLUGINS } from "@html_editor/backend/dynamic_field/dynamic_field_plugin";
import { isEmpty } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { isHtmlEmpty } from "@web/core/utils/html";
import { renderToMarkup } from "@web/core/utils/render";
import { HtmlMailField, htmlMailField } from "../html_mail_field/html_mail_field";
import { MailSuggestionPlugin } from "@mail/core/common/plugin/suggestion_plugin";
import { ContentExpandablePlugin } from "./content_expandable_plugin";
import { DisableBannerCommandsPlugin } from "./disable_banner_commands_plugin";
import { fillEmpty } from "@html_editor/utils/dom";
import { markup, onWillUnmount, useEffect } from "@odoo/owl";
import { SIGNATURE_CLASS } from "@html_editor/main/user_signature_plugin";
import { COMPOSER_TYPES } from "@mail/core/common/composer";
import { FullComposerBusPlugin } from "@mail/core/web/full_composer_bus_plugin";
import { useMaybePlugin } from "@mail/utils/common/hooks";

export class HtmlComposerMessageField extends HtmlMailField {
    setup() {
        super.setup();
        this.mailStore = useService("mail.store");
        this.fullComposerBus = useMaybePlugin(FullComposerBusPlugin)?.bus;
        if (this.fullComposerBus) {
            useBus(this.fullComposerBus, "ACCIDENTAL_DISCARD", (ev) => {
                const elContent = this.getNoSignatureElContent();
                ev.detail.onAccidentalDiscard(isEmpty(elContent));
            });
            useBus(this.fullComposerBus, "SAVE_CONTENT", (ev) => {
                const emailAddSignature = Boolean(
                    this.editor.editable.querySelector(`.${SIGNATURE_CLASS}`)
                );
                const composerHtml = markup(this.getNoSignatureElContent().innerHTML);
                ev.detail.onSaveContent({ composerHtml, emailAddSignature });
            });
            useBus(this.fullComposerBus, "ATTACHMENT_REMOVED", (ev) => {
                const attachmentElements = this.editor.editable.querySelectorAll(
                    `[data-attachment-id="${ev.detail.id}"]`
                );
                attachmentElements.forEach((element) => {
                    const parent = element.parentElement;
                    element.remove();
                    fillEmpty(parent);
                });
                this.editor.shared.history.commit();
            });
        }
        this.lastAttachmentSet = new Set();
        this.attachmentObserver = null;

        useEffect(() => {
            // Mailing mode does not go through the notification layout, which is what
            // fills the signature slot in comment mode: the signature has to be part
            // of the body itself, visible and editable, as soon as the composer opens.

            const record = this.props.record;
            const body = record.data[this.props.name] || "";
            const signature = this.mailStore.self_user?.getSignatureBlock();
            if (record.data.composition_mode !== "mass_mail" || !isHtmlEmpty(body) || !signature) {
                return;
            }

            record.update({
                [this.props.name]: markup`<br><br>${renderToMarkup("html_editor.Signature", {
                    signature,
                    signatureClass: SIGNATURE_CLASS,
                })}`,
            });
        });

        onWillUnmount(() => {
            if (this.attachmentObserver) {
                this.attachmentObserver.disconnect();
            }
        });
    }

    getConfig() {
        const config = super.getConfig(...arguments);
        config.Plugins = [
            ...config.Plugins.filter((plugin) => !["video"].includes(plugin.id)),
            DisableBannerCommandsPlugin,
            MailSuggestionPlugin,
        ];
        if (this.props.record.data.composition_comment_option === "reply_all") {
            config.Plugins.push(ContentExpandablePlugin);
        }
        if (!this.props.record.data.composition_batch) {
            config.Plugins = config.Plugins.filter(
                (plugin) => !DYNAMIC_FIELD_PLUGINS.includes(plugin)
            );
        }
        config.onAttachmentChange = async (attachment) => {
            // This only needs to happen for the composer for now
            if (
                !(
                    this.props.record.fieldNames.includes("attachment_ids") &&
                    this.props.record.resModel === "mail.compose.message"
                )
            ) {
                return;
            }
            await this.commitChanges();
            this.props.record.data.attachment_ids.linkTo(attachment.id, attachment);
        };
        const thread = this.env.services["mail.store"]?.["mail.thread"].get({
            model: this.props.record.data.model,
            id: JSON.parse(this.props.record.data.res_ids || "[]")[0],
        });
        config.onEditorReady = () => {
            this.attachmentObserver = new MutationObserver(
                this._commitChangesIfInlineAttachmentsHasChanged.bind(this)
            );
            this.attachmentObserver.observe(this.editor.editable, {
                attributes: true,
                attributeFilter: ["data-attachment-id"],
                childList: true, // to be notified when attachment links are removed
                subtree: true,
            });
        };
        const composerType = this.props.record.data.subtype_is_log
            ? COMPOSER_TYPES.NOTE
            : COMPOSER_TYPES.MESSAGE;
        config.composerPluginDependencies = {
            getComposerType: () => composerType,
            getThread: () => thread,
            // mentions are links only: the recipients are those of the form
            onInsertSuggestion: (option) => {
                if (option.cannedResponse) {
                    this.fullComposerBus?.trigger("INSERT_CANNED_RESPONSE", {
                        cannedResponse: option.cannedResponse,
                    });
                }
            },
        };
        config.resources = {
            ...config.resources,
            selectors_for_feff_providers: () =>
                "a.o_mail_redirect, a.o_channel_redirect, a.o-discuss-mention",
        };
        return config;
    }

    getNoSignatureElContent() {
        const elContent = this.editor.getElContent();
        this.editor.shared.userSignature.cleanSignatures({ rootClone: elContent });
        return elContent;
    }

    _commitChangesIfInlineAttachmentsHasChanged() {
        const nodes = this.editor.editable.querySelectorAll("[data-attachment-id]");
        const newAttachmentSet = new Set(
            [...nodes].map((node) => node.getAttribute("data-attachment-id"))
        );
        if (newAttachmentSet.symmetricDifference(this.lastAttachmentSet).size) {
            this.lastAttachmentSet = newAttachmentSet;
            this.commitChanges();
        }
    }
}

export const htmlComposerMessageField = {
    ...htmlMailField,
    additionalClasses: [...htmlMailField.additionalClasses, "ps-0", "o_mail_composer_message"],
    component: HtmlComposerMessageField,
};

registry.category("fields").add("html_composer_message", htmlComposerMessageField);
