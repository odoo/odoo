/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Composer } from "../composer/composer.js";
import { NavigableList } from "../composer/navigable_list.js";
import { MessageDeleteDialog } from "../core_ui/message_delete_dialog";
import { useSuggestion } from "../composer/suggestion_hook.js";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

import { isEventHandled, markEventHandled } from "../utils/misc";

patch(Composer.prototype, "mail/web", {
    setup() {
        this._super(...arguments);
        this.suggestion = useSuggestion();
    },

    hasSuggestions() {
        return this.suggestion.state.items.length > 0;
    },

    onKeydown(ev) {
        switch (ev.key) {
            case "ArrowUp": {
                if (this.hasSuggestions()) {
                    return;
                }
                break;
            }
            case "Enter": {
                if (isEventHandled(ev, "NavigableList.select")) {
                    return;
                }
                break;
            }
            case "Escape": {
                if (isEventHandled(ev, "NavigableList.close")) {
                    return;
                }
                break;
            }
        }
        this._super(ev);
    },

    getNavigableListProps() {
        return {
            anchorRef: this.ref.el,
            position: "top",
            onSelect: (ev, option) => {
                this.suggestion.insert(option);
                markEventHandled(ev, "composer.selectSuggestion");
            },
            sources: this.suggestion.state.items.map((mainOrExtraSuggestions) => {
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
                                    classList: "o-composer-suggestion o-composer-suggestion-thread",
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
            }),
        };
    },

    async sendMessage() {
        return this.processMessage(async (value) => {
            const thread =
                this.props.messageToReplyTo?.message?.originThread ?? this.props.composer.thread;
            const postData = {
                attachments: this.attachmentUploader.attachments,
                isNote:
                    this.props.composer.type === "note" ||
                    this.props.messageToReplyTo?.message?.isNote,
                rawMentions: this.suggestion.rawMentions,
                parentId: this.props.messageToReplyTo?.message?.id,
            };
            const message = await this.threadService.post(thread, value, postData);
            if (this.props.composer.thread.type === "mailbox") {
                this.env.services.notification.add(
                    sprintf(_t('Message posted on "%s"'), message.originThread.displayName),
                    { type: "info" }
                );
            }
            this.suggestion.clearRawMentions();
            this.props.messageToReplyTo?.cancel();
            if (this.typingNotified) {
                this.typingNotified = false;
                this.notifyIsTyping(false);
            }
        });
    },

    async editMessage() {
        if (this.ref.el.value) {
            await this.processMessage(async (value) =>
                this.messageService.update(
                    this.props.composer.message,
                    value,
                    this.attachmentUploader.attachments,
                    this.suggestion.rawMentions
                )
            );
        } else {
            this.env.services.dialog.add(MessageDeleteDialog, {
                message: this.props.composer.message,
                messageComponent: this.props.messageComponent,
            });
        }
        this.suggestion.clearRawMentions();
    },
});

patch(Composer, "mail/backend", {
    components: { ...Composer.components, NavigableList },
});
