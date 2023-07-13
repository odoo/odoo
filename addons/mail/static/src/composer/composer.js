/* @odoo-module */

import { AttachmentList } from "@mail/attachments/attachment_list";
import { useAttachmentUploader } from "@mail/attachments/attachment_uploader_hook";
import { useSelection } from "@mail/utils/hooks";
import { isDragSourceExternalFile, isEventHandled, markEventHandled } from "@mail/utils/misc";
import {
    Component,
    markup,
    onMounted,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { useDropzone } from "../dropzone/dropzone_hook";
import { useMessaging, useStore } from "../core/messaging_hook";
import { useEmojiPicker } from "../emoji_picker/emoji_picker";

import { sprintf } from "@web/core/utils/strings";
import { escapeAndCompactTextContent } from "../utils/format.js";
import { FileUploader } from "@web/views/fields/file_handler";
import { NavigableList } from "@mail/composer/navigable_list";
import { useSuggestion } from "@mail/composer/suggestion_hook";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { MessageConfirmDialog } from "../core_ui/message_confirm_dialog";

const EDIT_CLICK_TYPE = {
    CANCEL: "cancel",
    SAVE: "save",
};

/**
 * @typedef {Object} Props
 * @property {import("@mail/composer/composer_model").Composer} composer
 * @property {import("@mail/utils/hooks").MessageToReplyTo} messageToReplyTo
 * @property {import("@mail/utils/hooks").MessageEdition} [messageEdition]
 * @property {'compact'|'normal'|'extended'} [mode] default: 'normal'
 * @property {'message'|'note'|false} [type] default: false
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
    };
    static defaultProps = {
        mode: "normal",
        className: "",
        sidebar: true,
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
        "sidebar?",
        "type?",
    ];
    static template = "mail.Composer";

    setup() {
        this.SEND_KEYBIND_TO_SEND = markup(
            sprintf(_t("<samp>%(send_keybind)s</samp><i> to send</i>"), {
                send_keybind: this.sendKeybind,
            })
        );
        this.messaging = useMessaging();
        this.store = useStore();
        if (this.allowUpload) {
            this.attachmentUploader = useAttachmentUploader(
                this.thread ?? this.props.composer.message.originThread,
                { composer: this.props.composer }
            );
        }
        this.messageService = useState(useService("mail.message"));
        this.ui = useState(useService("ui"));
        /** @type {import("@mail/core/thread_service").ThreadService} */
        this.threadService = useService("mail.thread");
        this.ref = useRef("textarea");
        this.fakeTextarea = useRef("fakeTextarea");
        this.state = useState({
            autofocus: 0,
            active: true,
        });
        this.selection = useSelection({
            refName: "textarea",
            model: this.props.composer.selection,
            preserveOnClickAwayPredicate: async (ev) => {
                // Let event be handled by bubbling handlers first.
                await new Promise(setTimeout);
                return (
                    !this.isEventTrusted(ev) ||
                    isEventHandled(ev, "sidebar.openThread") ||
                    isEventHandled(ev, "emoji.selectEmoji") ||
                    isEventHandled(ev, "composer.clickOnAddEmoji") ||
                    isEventHandled(ev, "composer.clickOnAddAttachment") ||
                    isEventHandled(ev, "composer.selectSuggestion")
                );
            },
        });
        this.suggestion = this.store.user ? useSuggestion() : undefined;
        this.markEventHandled = markEventHandled;
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
                if (focus && this.ref.el) {
                    this.selection.restore();
                    this.ref.el.focus();
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
        useEffect(
            () => {
                this.ref.el.style.height = this.fakeTextarea.el.scrollHeight + "px";
            },
            () => [this.props.composer.textInputContent, this.ref.el]
        );
        useEffect(
            () => {
                if (!this.props.composer.forceCursorMove) {
                    return;
                }
                this.selection.restore();
                this.props.composer.forceCursorMove = false;
            },
            () => [this.props.composer.forceCursorMove]
        );
        onMounted(() => {
            this.ref.el.scrollTo({ top: 0, behavior: "instant" });
        });
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

    onClickCancelOrSaveEditText(ev) {
        if (this.props.composer.message && ev.target.dataset?.type === EDIT_CLICK_TYPE.CANCEL) {
            this.props.onDiscardCallback(ev);
        }
        if (this.props.composer.message && ev.target.dataset?.type === EDIT_CLICK_TYPE.SAVE) {
            this.editMessage(ev);
        }
    }

    get CANCEL_OR_SAVE_EDIT_TEXT() {
        return markup(
            sprintf(
                _t(
                    "<samp>%(cancel_keybind)s</samp><i> to <a href='#' data-type='%(cancel_type)s'>cancel</a></i>, <samp>%(save_keybind)s</samp><i> to <a href='#' data-type='%(save_type)s'>save</a></i>"
                ),
                {
                    cancel_keybind: _t("Escape"),
                    cancel_type: EDIT_CLICK_TYPE.CANCEL,
                    save_keybind: this.sendKeybind,
                    save_type: EDIT_CLICK_TYPE.SAVE,
                }
            )
        );
    }

    get SEND_TEXT() {
        return this.props.type === "note" ? _t("Log") : _t("Send");
    }

    get sendKeybind() {
        return this.props.mode === "extended" ? _t("CTRL-Enter") : _t("Enter");
    }

    get thread() {
        return (
            this.props.messageToReplyTo?.message?.originThread ?? this.props.composer.thread ?? null
        );
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
            (!this.props.composer.textInputContent && attachments.length === 0) ||
            attachments.some(({ uploading }) => Boolean(uploading))
        );
    }

    get hasSuggestions() {
        return Boolean(this.suggestion?.state.items);
    }

    get navigableListProps() {
        const props = {
            anchorRef: this.ref.el,
            position: this.thread?.type === "chatter" ? "bottom-fit" : "top-fit",
            placeholder: _t("Loading"),
            onSelect: (ev, option) => {
                this.suggestion.insert(option);
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
        ev.preventDefault();
        for (const file of ev.clipboardData.files) {
            this.attachmentUploader.uploadFile(file);
        }
    }

    onKeydown(ev) {
        switch (ev.key) {
            case "ArrowUp":
                if (this.props.messageEdition && this.props.composer.textInputContent === "") {
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
            default_body: escapeAndCompactTextContent(this.props.composer.textInputContent),
            default_model: this.props.composer.thread.model,
            default_partner_ids:
                this.props.type === "note"
                    ? []
                    : this.props.composer.thread.suggestedRecipients
                          .filter((recipient) => recipient.checked)
                          .map((recipient) => recipient.persona.id),
            default_res_ids: [this.props.composer.thread.id],
            default_subtype_xmlid: this.props.type === "note" ? "mail.mt_note" : "mail.mt_comment",
            mail_post_autofollow: this.props.composer.thread.hasWriteAccess,
        };
        const action = {
            name: this.props.type === "note" ? _t("Log note") : _t("Compose Email"),
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

    clear() {
        this.attachmentUploader?.clear();
        this.threadService.clearComposer(this.props.composer);
    }

    onClickAddEmoji(ev) {
        markEventHandled(ev, "composer.clickOnAddEmoji");
    }

    isEventTrusted(ev) {
        // Allow patching during tests
        return ev.isTrusted;
    }

    async processMessage(cb) {
        const el = this.ref.el;
        const attachments = this.props.composer.attachments;
        if (
            el.value.trim() ||
            (attachments.length > 0 && attachments.every(({ uploading }) => !uploading)) ||
            (this.message && this.message.attachments.length > 0)
        ) {
            if (!this.state.active) {
                return;
            }
            this.state.active = false;
            await cb(el.value);
            if (this.props.onPostCallback) {
                this.props.onPostCallback();
            }
            this.clear();
            this.state.active = true;
            el.focus();
        } else if (attachments.some(({ uploading }) => Boolean(uploading))) {
            this.env.services.notification.add(
                this.env._t("Please wait while the file is uploading."),
                { type: "warning" }
            );
        }
    }

    async sendMessage() {
        await this.processMessage(async (value) => {
            const postData = {
                attachments: this.props.composer.attachments,
                isNote: this.props.type === "note",
                rawMentions: this.props.composer.rawMentions,
                parentId: this.props.messageToReplyTo?.message?.id,
            };
            const message = await this.threadService.post(this.thread, value, postData);
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
        if (this.ref.el.value || this.props.composer.message.attachments.length > 0) {
            await this.processMessage(async (value) =>
                this.messageService.edit(
                    this.props.composer.message,
                    value,
                    this.props.composer.attachments,
                    this.props.composer.rawMentions
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
        const textContent = this.ref.el.value;
        const firstPart = textContent.slice(0, this.props.composer.selection.start);
        const secondPart = textContent.slice(this.props.composer.selection.end, textContent.length);
        this.props.composer.textInputContent = firstPart + str + secondPart;
        this.selection.moveCursor((firstPart + str).length);
        this.state.autofocus++;
    }

    onFocusin() {
        this.props.composer.isFocused = true;
        if (this.props.composer.thread) {
            this.threadService.markAsRead(this.props.composer.thread);
        }
    }
}
