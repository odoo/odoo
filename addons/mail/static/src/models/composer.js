/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'Composer',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @private
         */
        _reset() {
            this.update({
                attachments: clear(),
                rawMentionedChannels: clear(),
                rawMentionedPartners: clear(),
                textInputContent: clear(),
                textInputCursorEnd: clear(),
                textInputCursorStart: clear(),
                textInputSelectionDirection: clear(),
            });
            for (const composerView of this.composerViews) {
                composerView.update({ hasToRestoreContent: true });
            }
        },
    },
    fields: {
        activeThread: one('Thread', {
            compute() {
                if (this.messageViewInEditing && this.messageViewInEditing.message && this.messageViewInEditing.message.originThread) {
                    return this.messageViewInEditing.message.originThread;
                }
                if (this.thread) {
                    return this.thread;
                }
                return clear();
            },
            required: true,
        }),
        /**
         * States which attachments are currently being created in this composer.
         */
        attachments: many('Attachment', {
            inverse: 'composer',
        }),
        canPostMessage: attr({
            compute() {
                if (this.thread && !this.textInputContent && this.attachments.length === 0) {
                    return false;
                }
                return !this.hasUploadingAttachment && !this.isPostingMessage;
            },
            default: false,
        }),
        composerViews: many('ComposerView', {
            inverse: 'composer',
            isCausal: true,
        }),
        /**
         * This field determines whether some attachments linked to this
         * composer are being uploaded.
         */
        hasUploadingAttachment: attr({
            compute() {
                return this.attachments.some(attachment => attachment.isUploading);
            },
        }),
        /**
         * If true composer will log a note, else a comment will be posted.
         */
        isLog: attr({
            default: true,
        }),
        /**
         * Determines whether a post_message request is currently pending.
         */
        isPostingMessage: attr(),
        mentionedChannels: many('Thread', {
            /**
             * Detects if mentioned channels are still in the composer text input content
             * and removes them if not.
             */
            compute() {
                const mentionedChannels = [];
                // ensure the same mention is not used multiple times if multiple
                // channels have the same name
                const namesIndex = {};
                for (const channel of this.rawMentionedChannels) {
                    const fromIndex = namesIndex[channel.name] !== undefined
                        ? namesIndex[channel.name] + 1 :
                        0;
                    const index = this.textInputContent.indexOf(`#${channel.name}`, fromIndex);
                    if (index === -1) {
                        continue;
                    }
                    namesIndex[channel.name] = index;
                    mentionedChannels.push(channel);
                }
                return mentionedChannels;
            },
        }),
        mentionedPartners: many('Partner', {
            /**
             * Detects if mentioned partners are still in the composer text input content
             * and removes them if not.
             */
            compute() {
                const mentionedPartners = [];
                // ensure the same mention is not used multiple times if multiple
                // partners have the same name
                const namesIndex = {};
                for (const partner of this.rawMentionedPartners) {
                    const fromIndex = namesIndex[partner.name] !== undefined
                        ? namesIndex[partner.name] + 1 :
                        0;
                    const index = this.textInputContent.indexOf(`@${partner.name}`, fromIndex);
                    if (index === -1) {
                        continue;
                    }
                    namesIndex[partner.name] = index;
                    mentionedPartners.push(partner);
                }
                return mentionedPartners;
            },
        }),
        messageViewInEditing: one('MessageView', {
            identifying: true,
            inverse: 'composerForEditing',
        }),
        /**
         * Placeholder displayed in the composer textarea when it's empty
         */
        placeholder: attr({
            compute() {
                if (!this.thread) {
                    return "";
                }
                if (this.thread.channel) {
                    if (this.thread.channel.correspondent) {
                        return sprintf(this.env._t("Message %s..."), this.thread.channel.correspondent.nameOrDisplayName);
                    }
                    return sprintf(this.env._t("Message #%s..."), this.thread.displayName);
                }
                if (this.isLog) {
                    return this.env._t("Log an internal note...");
                }
                return this.env._t("Send a message to followers...");
            },
        }),
        rawMentionedChannels: many('Thread'),
        rawMentionedPartners: many('Partner'),
        /**
         * Determines the extra `Partner` (on top of existing followers)
         * that will receive the message being composed by `this`, and that will
         * also be added as follower of `this.activeThread`.
         */
        recipients: many('Partner', {
            compute() {
                const recipients = [...this.mentionedPartners];
                if (this.activeThread && !this.isLog) {
                    for (const recipient of this.activeThread.suggestedRecipientInfoList) {
                        if (recipient.partner && recipient.isSelected) {
                            recipients.push(recipient.partner);
                        }
                    }
                }
                return recipients;
            },
        }),
        textInputContent: attr({
            default: "",
        }),
        textInputCursorEnd: attr({
            default: 0,
        }),
        textInputCursorStart: attr({
            default: 0,
        }),
        textInputSelectionDirection: attr({
            default: "none",
        }),
        /**
         * States the thread which this composer represents the state (if any).
         */
        thread: one('Thread', {
            identifying: true,
            inverse: 'composer',
        }),
    },
});
