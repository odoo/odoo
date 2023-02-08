/* @odoo-module */

import { AttachmentList } from "@mail/new/attachments/attachment_list";
import { useAttachmentUploader } from "@mail/new/attachments/attachment_uploader_hook";
import { onExternalClick, useSelection } from "@mail/new/utils/hooks";
import { isDragSourceExternalFile, isEventHandled, markEventHandled } from "@mail/new/utils/misc";
import { Component, onMounted, useChildSubEnv, useEffect, useRef, useState } from "@odoo/owl";
import { useDropzone } from "../dropzone/dropzone_hook";
import { useMessaging, useStore } from "../core/messaging_hook";
import { useEmojiPicker } from "../emoji_picker/emoji_picker";

import { sprintf } from "@web/core/utils/strings";
import { escapeAndCompactTextContent } from "../utils/format.js";
import { FileUploader } from "@web/views/fields/file_handler";
import { Typing } from "./typing";
import { NavigableList } from "@mail/new/composer/navigable_list";
import { useDebounced } from "@web/core/utils/timing";
import { useSuggestion } from "@mail/new/composer/suggestion_hook";
import { browser } from "@web/core/browser/browser";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { MessageDeleteDialog } from "../core_ui/message_delete_dialog";

export const SHORT_TYPING = 5000;
export const LONG_TYPING = 50000;

/**
 * @typedef {Object} Props
 * @property {import("@mail/new/composer/composer_model").Composer} composer
 * @property {import("@mail/new/utils/hooks").MessageToReplyTo} messageToReplyTo
 * @extends {Component<Props, Env>}
 */
export class Composer extends Component {
    static components = {
        AttachmentList,
        FileUploader,
        Typing,
        NavigableList,
    };
    static defaultProps = {
        mode: "normal",
    }; // mode = compact, normal, extended
    static props = [
        "composer",
        "autofocus?",
        "highlightReplyTo?",
        "messageToReplyTo?",
        "onDiscardCallback?",
        "onPostCallback?",
        "mode?",
        "placeholder?",
        "dropzoneRef?",
        "messageEdition?",
        "messageComponent?",
    ];
    static template = "mail.composer";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        if (this.allowUpload) {
            this.attachmentUploader = useAttachmentUploader(
                this.props.messageToReplyTo?.message?.originThread ??
                    this.props.composer.thread ??
                    this.props.composer.message.originThread,
                this.props.composer
            );
        }
        this.messageService = useState(useService("mail.message"));
        /** @type {import("@mail/new/core/thread_service").ThreadService} */
        this.threadService = useService("mail.thread");
        this.ref = useRef("textarea");
        this.typingNotified = false;
        this.state = useState({
            autofocus: 0,
            active: true,
        });
        this.stopTyping = useDebounced(() => {
            this.notifyIsTyping(false);
            this.typingNotified = false;
        }, SHORT_TYPING);
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
        if (this.props.dropzoneRef && this.allowUpload) {
            useDropzone(this.props.dropzoneRef, (ev) => {
                if (isDragSourceExternalFile(ev.dataTransfer)) {
                    for (const file of ev.dataTransfer.files) {
                        this.attachmentUploader.uploadFile(file);
                    }
                }
            });
        }
        if (this.props.messageEdition) {
            this.props.messageEdition.composerOfThread = this;
        }
        useChildSubEnv({
            inComposer: true,
        });
        useEmojiPicker("emoji-picker", {
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
                this.ref.el.style.height = "1px";
                this.ref.el.style.height = this.ref.el.scrollHeight + "px";
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
        onExternalClick("composer", async (ev) => {
            // Let event be handled by bubbling handlers first.
            await new Promise(setTimeout);
            if (isEventHandled(ev, "message.replyTo") || isEventHandled(ev, "emoji.selectEmoji")) {
                return;
            }
            this.props.messageToReplyTo?.cancel();
        });
    }

    onInput(ev) {
        if (!this.typingNotified && !ev.target.value.startsWith("/")) {
            this.notifyIsTyping();
            this.typingNotified = true;
            browser.setTimeout(() => {
                this.typingNotified = false;
            }, LONG_TYPING);
        }
        this.stopTyping();
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
            (!this.props.composer.textInputContent && attachments.length === 0) ||
            attachments.some(({ uploading }) => Boolean(uploading))
        );
    }

    get hasSuggestions() {
        return this.suggestion?.state.items.length > 0;
    }

    get navigableListProps() {
        return {
            anchorRef: this.ref.el,
            position: "top",
            onSelect: (ev, option) => {
                this.suggestion?.insert(option);
                markEventHandled(ev, "composer.selectSuggestion");
            },
            sources: this.suggestion
                ? this.suggestion.state.items.map((mainOrExtraSuggestions) => {
                      switch (mainOrExtraSuggestions.type) {
                          case "Partner":
                              return {
                                  placeholder: "Loading",
                                  optionTemplate: "mail.Composer.suggestionPartner",
                                  options: mainOrExtraSuggestions.suggestions.map((suggestion) => {
                                      return {
                                          label: suggestion.name,
                                          partner: suggestion,
                                          classList:
                                              "o-composer-suggestion o-composer-suggestion-partner",
                                      };
                                  }),
                              };
                          case "Thread":
                              return {
                                  placeholder: "Loading",
                                  optionTemplate: "mail.Composer.suggestionThread",
                                  options: mainOrExtraSuggestions.suggestions.map((suggestion) => {
                                      return {
                                          label: suggestion.displayName,
                                          thread: suggestion,
                                          classList:
                                              "o-composer-suggestion o-composer-suggestion-thread",
                                      };
                                  }),
                              };
                          case "ChannelCommand":
                              return {
                                  placeholder: "Loading",
                                  optionTemplate: "mail.Composer.suggestionChannelCommand",
                                  options: mainOrExtraSuggestions.suggestions.map((suggestion) => {
                                      return {
                                          label: suggestion.name,
                                          help: suggestion.help,
                                          classList:
                                              "o-composer-suggestion o-composer-suggestion-channel-command",
                                      };
                                  }),
                              };
                          case "CannedResponse":
                              return {
                                  placeholder: "Loading",
                                  optionTemplate: "mail.Composer.suggestionCannedResponse",
                                  options: mainOrExtraSuggestions.suggestions.map((suggestion) => {
                                      return {
                                          name: suggestion.name,
                                          label: suggestion.substitution,
                                          classList:
                                              "o-composer-suggestion o-composer-suggestion-canned-response",
                                      };
                                  }),
                              };
                          default:
                              return {
                                  options: [],
                              };
                      }
                  })
                : [],
        };
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
                if (this.hasSuggestions) {
                    return;
                }
                if (this.props.messageEdition) {
                    const messageToEdit = this.props.composer.thread.lastEditableMessageOfSelf;
                    if (messageToEdit) {
                        this.props.messageEdition.editingMessage = messageToEdit;
                    }
                }
                break;
            case "Enter": {
                if (isEventHandled(ev, "NavigableList.select")) {
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
            default_partner_ids: this.props.composer.thread.suggestedRecipients.map(
                (partner) => partner.id
            ),
            default_res_ids: [this.props.composer.thread.id],
            default_subtype_xmlid:
                this.props.composer.type === "note" ? "mail.mt_note" : "mail.mt_comment",
            mail_post_autofollow: this.props.composer.thread.hasWriteAccess,
        };
        const action = {
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
            this.state.active = true;
            this.clear();
            el.focus();
        } else if (attachments.some(({ uploading }) => Boolean(uploading))) {
            this.env.services.notification.add(
                this.env._t("Please wait while the file is uploading."),
                { type: "warning" }
            );
        }
    }

    async sendMessage() {
        return this.processMessage(async (value) => {
            const thread =
                this.props.messageToReplyTo?.message?.originThread ?? this.props.composer.thread;
            const postData = {
                attachments: this.props.composer.attachments,
                isNote:
                    this.props.composer.type === "note" ||
                    this.props.messageToReplyTo?.message?.isNote,
                rawMentions: this.suggestion ? this.suggestion.rawMentions : [],
                parentId: this.props.messageToReplyTo?.message?.id,
            };
            const message = await this.threadService.post(thread, value, postData);
            if (this.props.composer.thread.type === "mailbox") {
                this.env.services.notification.add(
                    sprintf(_t('Message posted on "%s"'), message.originThread.displayName),
                    { type: "info" }
                );
            }
            this.suggestion?.clearRawMentions();
            this.props.messageToReplyTo?.cancel();
            if (this.typingNotified) {
                this.typingNotified = false;
                this.notifyIsTyping(false);
            }
        });
    }

    /**
     * Notify the server of the current typing status
     *
     * @param {boolean} [is_typing=true]
     */
    notifyIsTyping(is_typing = true) {
        if (["chat", "channel", "group"].includes(this.thread?.type)) {
            this.messaging.rpc(
                "/mail/channel/notify_typing",
                {
                    channel_id: this.thread.id,
                    is_typing,
                },
                { silent: true }
            );
        }
    }

    async editMessage() {
        if (this.ref.el.value) {
            await this.processMessage(async (value) =>
                this.messageService.update(
                    this.props.composer.message,
                    value,
                    this.props.composer.attachments,
                    this.suggestion?.rawMentions
                )
            );
        } else {
            this.env.services.dialog.add(MessageDeleteDialog, {
                message: this.props.composer.message,
                messageComponent: this.props.messageComponent,
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
