/* @odoo-module */

import { AttachmentList } from "@mail/attachments/attachment_list";
import { useAttachmentUploader } from "@mail/attachments/attachment_uploader_hook";
import { isDragSourceExternalFile, isEventHandled, markEventHandled } from "@mail/utils/misc";
import {
    Component,
    onWillStart,
    onMounted,
    useSubEnv,
    useChildSubEnv,
    useRef,
    useEffect,
    useState,
} from "@odoo/owl";
import { useDropzone } from "../dropzone/dropzone_hook";
import { useMessaging, useStore } from "../core/messaging_hook";
import { useEmojiPicker } from "../emoji_picker/emoji_picker";

import { sprintf } from "@web/core/utils/strings";
import { getWysiwygClass } from "web_editor.loader";
import legacyEnv from "web.commonEnv";
import { ComponentAdapter } from "web.OwlCompatibility";
import { FileUploader } from "@web/views/fields/file_handler";
import { NavigableList } from "@mail/composer/navigable_list";
import { useSuggestion } from "@mail/composer/suggestion_hook";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { MessageConfirmDialog } from "../core_ui/message_confirm_dialog";
import { setCursorEnd } from "@web_editor/js/editor/odoo-editor/src/utils/utils";

// See odoo/addons/web_editor/static/src/js/backend/html_field.js
// for the original implementation of this component.
// This is for reducing the bundle denpendency of the composer in public env.
class HtmlFieldWysiwygAdapterComponent extends ComponentAdapter {
    setup() {
        super.setup();
        useSubEnv(legacyEnv);

        let started = false;
        onMounted(() => {
            if (!started) {
                this.props.startWysiwyg(this.widget);
                started = true;
            }
        });
    }

    updateWidget(newProps) {
        const lastValue = String(this.props.widgetArgs[0].value || "");
        const lastRecordInfo = this.props.widgetArgs[0].recordInfo;
        const lastCollaborationChannel = this.props.widgetArgs[0].collaborationChannel;
        const newValue = String(newProps.widgetArgs[0].value || "");
        const newRecordInfo = newProps.widgetArgs[0].recordInfo;
        const newCollaborationChannel = newProps.widgetArgs[0].collaborationChannel;

        if (
            (stripHistoryIds(newValue) !== stripHistoryIds(newProps.editingValue) &&
                stripHistoryIds(lastValue) !== stripHistoryIds(newValue)) ||
            !_.isEqual(lastRecordInfo, newRecordInfo) ||
            !_.isEqual(lastCollaborationChannel, newCollaborationChannel)
        ) {
            this.widget.resetEditor(newValue, newProps.widgetArgs[0]);
            this.env.onWysiwygReset && this.env.onWysiwygReset();
        }
    }
    renderWidget() {}
}

function stripHistoryIds(value) {
    return (value && value.replace(/\sdata-last-history-steps="[^"]*?"/, "")) || value;
}

/**
 * @typedef {Object} Props
 * @property {import("@mail/composer/composer_model").Composer} composer
 * @property {import("@mail/utils/hooks").MessageToReplyTo} messageToReplyTo
 * @property {import("@mail/utils/hooks").MessageEdition} [messageEdition]
 * @property {'compact'|'normal'|'extended'} [mode] default: 'normal'
 * @property {string} [placeholder]
 * @property {string} [className]
 * @property {function} [onDiscardCallback]
 * @property {function} [onPostCallback]
 * @property {Component} [messageComponent]
 * @property {number} [autofocus]
 * @property {import("@web/core/utils/hooks").Ref} [dropzoneRef]
 * @extends {Component<Props, Env>}
 */
export class Composer extends Component {
    static components = {
        AttachmentList,
        FileUploader,
        NavigableList,
        HtmlFieldWysiwygAdapterComponent,
    };
    static defaultProps = {
        mode: "normal",
        className: "",
    };
    static props = [
        "composer",
        "autofocus?",
        "messageToReplyTo?",
        "onDiscardCallback?",
        "onPostCallback?",
        "mode?",
        "placeholder?",
        "dropzoneRef?",
        "messageEdition?",
        "messageComponent?",
        "className?",
    ];
    static template = "mail.Composer";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        if (this.allowUpload) {
            this.attachmentUploader = useAttachmentUploader(
                this.props.messageToReplyTo?.message?.originThread ??
                    this.props.composer.thread ??
                    this.props.composer.message.originThread,
                { composer: this.props.composer }
            );
        }
        this.messageService = useState(useService("mail.message"));
        /** @type {import("@mail/core/thread_service").ThreadService} */
        this.threadService = useService("mail.thread");
        this.wysiwygAreaRef = useRef("wysiwygArea");
        this.state = useState({
            autofocus: 0,
            active: true,
        });
        onWillStart(async () => {
            this.Wysiwyg = await getWysiwygClass();
        });
        this.suggestion = this.store.user ? useSuggestion() : undefined;
        if (this.props.dropzoneRef && this.allowUpload) {
            useDropzone(
                this.props.dropzoneRef,
                (ev) => {
                    if (isDragSourceExternalFile(ev.dataTransfer)) {
                        for (const file of ev.dataTransfer.files) {
                            this.attachmentUploader.uploadFile(file);
                        }
                    }
                },
                "o-mail-Composer-dropzone"
            );
        }
        if (this.props.messageEdition) {
            this.props.messageEdition.composerOfThread = this;
        }
        useChildSubEnv({
            inComposer: true,
        });
        useEmojiPicker(useRef("emoji-picker"), {
            onSelect: (str) => this.addEmoji(str),
            onClose: () => this.state.autofocus++,
        });
        useEffect(
            (focus) => {
                if (focus && this.wysiwyg) {
                    // TODO: restore selection, the composer.range is lost when the DOM is updated.
                    this.wysiwyg.focus();
                }
            },
            () => [this.props.autofocus + this.state.autofocus, this.props.placeholder]
        );
        useEffect(
            (rThread, cThread) => {
                if (cThread && rThread === cThread) {
                    this.state.autofocus++;
                }
            },
            () => [this.props.messageToReplyTo?.thread, this.props.composer.thread]
        );
    }

    async startWysiwyg(wysiwyg) {
        this.wysiwyg = wysiwyg;
        await this.wysiwyg.startEdition();
        this.wysiwyg.odooEditor.editable.addEventListener("click", () => {
            this.update();
        });
        this.wysiwyg.odooEditor.editable.addEventListener("keyup", (ev) => {
            this.onKeyup(ev);
        });
        this.wysiwyg.odooEditor.editable.addEventListener("keydown", (ev) => {
            this.onKeydown(ev);
        });
        this.wysiwyg.odooEditor.editable.addEventListener("focusin", () => {
            this.props.composer.isFocused = true;
            if (this.props.composer.thread) {
                this.threadService.markAsRead(this.props.composer.thread);
            }
        });
        this.wysiwyg.odooEditor.editable.addEventListener("focusout", () => {
            this.props.composer.isFocused = false;
        });
        this.wysiwyg.odooEditor.editable.addEventListener("paste", (ev) => {
            this.onPaste(ev);
        });
        this.wysiwyg.focus();
        this.update();
    }

    wysiwygOptions() {
        return {
            autostart: false,
            collaborative: false,
            disableToolbar: true,
            disableTabAction: true,
            disbaleImagesOnPaste: true,
            isPlaceholderHintPriority: true,
            isPlaceholderHintTemporary: false,
            placeholder: this.placeholder,
            powerboxFilters: [
                () => {
                    return [];
                },
            ],
            value: this.props.composer.wysiwygValue,
        };
    }

    get placeholder() {
        if (this.props.placeholder) {
            return this.props.placeholder;
        }
        if (this.thread) {
            if (this.thread.type === "channel") {
                return sprintf(_t("Message #%(thread name)s…"), {
                    "thread name": this.thread.displayName,
                });
            }
            return sprintf(_t("Message %(thread name)s…"), {
                "thread name": this.thread.displayName,
            });
        }
        return "";
    }

    get thread() {
        return this.props.composer.thread ?? null;
    }

    get allowUpload() {
        return true;
    }

    get message() {
        return this.props.composer.message ?? null;
    }

    get isSendButtonDisabled() {
        const attachments = this.props.composer.attachments;
        return (
            !this.state.active ||
            (this.wysiwyg?.odooEditor?.editable.textContent.trim() === "" &&
                attachments.length === 0) ||
            attachments.some(({ uploading }) => Boolean(uploading))
        );
    }

    get hasSuggestions() {
        return Boolean(this.suggestion?.state.items);
    }

    get navigableListProps() {
        const props = {
            anchorRef: this.wysiwygAreaRef.el,
            position: this.thread?.type === "chatter" ? "bottom-fit" : "top-fit",
            placeholder: _t("Loading"),
            onSelect: (ev, option) => {
                this.suggestion.insert(option, this.update.bind(this));
                markEventHandled(ev, "composer.selectSuggestion");
            },
            options: [],
        };
        if (!this.hasSuggestions) {
            return props;
        }
        const suggestions = Array(
            ...this.suggestion.state.items.mainSuggestions,
            ...this.suggestion.state.items.extraSuggestions
        );
        switch (this.suggestion.state.items.type) {
            case "Partner":
                return {
                    ...props,
                    optionTemplate: "mail.Composer.suggestionPartner",
                    options: suggestions.map((suggestion) => {
                        return {
                            label: suggestion.name,
                            partner: suggestion,
                            classList: "o-mail-Composer-suggestion",
                        };
                    }),
                };
            case "Thread":
                return {
                    ...props,
                    optionTemplate: "mail.Composer.suggestionThread",
                    options: suggestions.map((suggestion) => {
                        return {
                            label: suggestion.displayName,
                            thread: suggestion,
                            classList: "o-mail-Composer-suggestion",
                        };
                    }),
                };
            case "ChannelCommand":
                return {
                    ...props,
                    optionTemplate: "mail.Composer.suggestionChannelCommand",
                    options: suggestions.map((suggestion) => {
                        return {
                            label: suggestion.name,
                            help: suggestion.help,
                            classList: "o-mail-Composer-suggestion",
                        };
                    }),
                };
            case "CannedResponse":
                return {
                    ...props,
                    optionTemplate: "mail.Composer.suggestionCannedResponse",
                    options: suggestions.map((suggestion) => {
                        return {
                            name: suggestion.name,
                            label: suggestion.substitution,
                            classList: "o-mail-Composer-suggestion",
                        };
                    }),
                };
            default:
                return props;
        }
    }

    /**
     * This doesn't work on firefox https://bugzilla.mozilla.org/show_bug.cgi?id=1699743
     */
    onPaste(ev) {
        if (!this.allowUpload) {
            return;
        }
        if (!ev.clipboardData?.items) {
            return;
        }
        if (ev.clipboardData.files.length === 0) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        for (const file of ev.clipboardData.files) {
            this.attachmentUploader.uploadFile(file);
        }
    }

    onKeyup(ev) {
        if (
            this.hasSuggestions &&
            (ev.key === "ArrowUp" ||
                ev.key === "ArrowDown" ||
                ev.key === "Tab" ||
                ev.key === "Escape")
        ) {
            return;
        }
        this.update();
    }

    onKeydown(ev) {
        switch (ev.key) {
            case "ArrowUp":
                if (this.hasSuggestions) {
                    return;
                }
                if (
                    this.props.messageEdition &&
                    this.wysiwyg?.odooEditor.editable.textContent === ""
                ) {
                    const messageToEdit = this.props.composer.thread.lastEditableMessageOfSelf;
                    if (messageToEdit) {
                        this.props.messageEdition.editingMessage = messageToEdit;
                    }
                }
                break;
            case "Enter": {
                if (isEventHandled(ev, "NavigableList.select") || !this.state.active) {
                    ev.preventDefault();
                    return;
                }
                const shouldPost = this.props.mode === "extended" ? ev.ctrlKey : !ev.shiftKey;
                if (!shouldPost) {
                    if (!ev.shiftKey && this.props.mode === "extended") {
                        ev.preventDefault();
                        this.wysiwyg.odooEditor._applyCommand("oShiftEnter");
                    }
                    return;
                }
                ev.preventDefault(); // to prevent useless return
                if (this.props.composer.message) {
                    this.editMessage();
                } else {
                    this.sendMessage();
                }
                break;
            }
            case "Escape":
                if (isEventHandled(ev, "NavigableList.close")) {
                    return;
                }
                if (this.props.onDiscardCallback) {
                    this.props.onDiscardCallback();
                    markEventHandled(ev, "Composer.discard");
                }
                break;
        }
    }

    onClickAddAttachment(ev) {
        markEventHandled(ev, "composer.clickOnAddAttachment");
        this.state.autofocus++;
    }

    async onClickFullComposer(ev) {
        const attachmentIds = this.props.composer.attachments.map((attachment) => attachment.id);
        const context = {
            default_attachment_ids: attachmentIds,
            default_body: this.props.composer.wysiwygValue,
            default_model: this.props.composer.thread.model,
            default_partner_ids: this.props.composer.thread.suggestedRecipients.map(
                (partner) => partner.id
            ),
            default_res_ids: [this.props.composer.thread.id],
            default_subtype_xmlid:
                this.props.composer.type === "note" ? "mail.mt_note" : "mail.mt_comment",
            mail_post_autofollow: this.props.composer.thread.hasWriteAccess,
        };
        const action = {
            name: this.props.composer.type === "note" ? _t("Log note") : _t("Compose Email"),
            type: "ir.actions.act_window",
            res_model: "mail.compose.message",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: context,
        };
        const options = {
            onClose: () => {
                this.clear();
                if (this.props.composer.thread) {
                    this.threadService.fetchNewMessages(this.props.composer.thread);
                }
            },
        };
        await this.env.services.action.doAction(action, options);
    }

    update() {
        const value = this.wysiwyg?.getValue();
        const lastValue = (this.props.composer.wysiwygValue || "").toString();
        if (
            value !== null &&
            !(!lastValue && stripHistoryIds(value) === "<p><br></p>") &&
            stripHistoryIds(value) !== stripHistoryIds(lastValue)
        ) {
            this.props.composer.wysiwygValue = value;
            this.props.composer.range = this.wysiwyg.getDeepRange();
        }
        const range = this.wysiwyg?.getDeepRange();
        this.props.composer.range = range;
    }

    clear() {
        this.attachmentUploader?.clear();
        this.threadService.clearComposer(this.props.composer);
        this.wysiwyg.odooEditor.resetContent();
    }

    onClickAddEmoji(ev) {
        markEventHandled(ev, "composer.clickOnAddEmoji");
    }

    isEventTrusted(ev) {
        // Allow patching during tests
        return ev.isTrusted;
    }

    async processMessage(cb) {
        const attachments = this.props.composer.attachments;
        if (
            this.wysiwyg?.odooEditor.editable.textContent ||
            (attachments.length > 0 && attachments.every(({ uploading }) => !uploading)) ||
            (this.message && this.message.attachments.length > 0)
        ) {
            if (!this.state.active) {
                return;
            }
            this.state.active = false;
            await cb(
                this.wysiwyg?.odooEditor.editable.textContent,
                this.props.composer.wysiwygValue
            );
            if (this.props.onPostCallback) {
                this.props.onPostCallback();
            }
            this.clear();
            this.state.active = true;
            this.wysiwyg.odooEditor.editable.focus();
            this.update();
        } else if (attachments.some(({ uploading }) => Boolean(uploading))) {
            this.env.services.notification.add(
                this.env._t("Please wait while the file is uploading."),
                { type: "warning" }
            );
        }
    }

    async sendMessage() {
        await this.processMessage(async (textContent, body) => {
            const thread =
                this.props.messageToReplyTo?.message?.originThread ?? this.props.composer.thread;
            const postData = {
                attachments: this.props.composer.attachments,
                isNote:
                    this.props.composer.type === "note" ||
                    this.props.messageToReplyTo?.message?.isNote,
                rawMentions: this.props.composer.rawMentions,
                parentId: this.props.messageToReplyTo?.message?.id,
            };
            const message = await this.threadService.post(thread, textContent, body, postData);
            if (this.props.composer.thread.type === "mailbox") {
                this.env.services.notification.add(
                    sprintf(_t('Message posted on "%s"'), message.originThread.displayName),
                    { type: "info" }
                );
            }
            this.suggestion?.clearRawMentions();
            this.props.messageToReplyTo?.cancel();
        });
    }

    async editMessage() {
        if (
            this.wysiwyg?.odooEditor.editable.textContent ||
            this.props.composer.message.attachments.length > 0
        ) {
            await this.processMessage(async (textContent, body) =>
                this.messageService.edit(
                    this.props.composer.message,
                    body,
                    this.props.composer.attachments
                )
            );
        } else {
            this.env.services.dialog.add(MessageConfirmDialog, {
                message: this.props.composer.message,
                messageComponent: this.props.messageComponent,
                onConfirm: () => this.messageService.delete(this.message),
                prompt: _t("Are you sure you want to delete this message?"),
            });
        }
        this.suggestion?.clearRawMentions();
    }

    addEmoji(str) {
        this.wysiwyg.odooEditor.historyPauseSteps();
        const emoji = document.createTextNode(str);
        if (this.props.composer.range.collapsed) {
            // To avoid buggy behavior when inserting emoji after initializing the editor,
            // we need to check if the content is empty and if so, we need to replace the
            // content with the emoji. Othwerwise, we will have `</br>str`.
            if (this.wysiwyg.getValue() === "<p><br></p>") {
                const editable = this.wysiwyg.odooEditor.editable;
                editable.firstChild.insertBefore(emoji, editable.firstChild.firstChild);
                editable.firstChild.firstChild.nextSibling.remove();
            } else {
                this.props.composer.range.insertNode(emoji);
            }
        } else {
            this.props.composer.range.deleteContents();
            this.props.composer.range.insertNode(emoji);
        }
        setCursorEnd(emoji, false);
        this.wysiwyg.odooEditor.historyUnpauseSteps();
        this.wysiwyg.odooEditor.historyStep();
        this.state.autofocus++;
        this.update();
    }
}
