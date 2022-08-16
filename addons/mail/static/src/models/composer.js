/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, replace, unlink } from '@mail/model/model_field_command';
import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'Composer',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @private
         * @returns {Thread}
         */
        _computeActiveThread() {
            if (this.messageViewInEditing && this.messageViewInEditing.message && this.messageViewInEditing.message.originThread) {
                return replace(this.messageViewInEditing.message.originThread);
            }
            if (this.thread) {
                return replace(this.thread);
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeCanPostMessage() {
            if (this.thread && !this.textInputContent && this.attachments.length === 0) {
                return false;
            }
            return !this.hasUploadingAttachment && !this.isPostingMessage;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasUploadingAttachment() {
            return this.attachments.some(attachment => attachment.isUploading);
        },
        /**
         * Detects if mentioned partners are still in the composer text input content
         * and removes them if not.
         *
         * @private
         * @returns {Partner[]}
         */
        _computeMentionedPartners() {
            const unmentionedPartners = [];
            // ensure the same mention is not used multiple times if multiple
            // partners have the same name
            const namesIndex = {};
            for (const partner of this.mentionedPartners) {
                const fromIndex = namesIndex[partner.name] !== undefined
                    ? namesIndex[partner.name] + 1 :
                    0;
                const index = this.textInputContent.indexOf(`@${partner.name}`, fromIndex);
                if (index !== -1) {
                    namesIndex[partner.name] = index;
                } else {
                    unmentionedPartners.push(partner);
                }
            }
            return unlink(unmentionedPartners);
        },
        /**
         * Detects if mentioned channels are still in the composer text input content
         * and removes them if not.
         *
         * @private
         * @returns {Partner[]}
         */
        _computeMentionedChannels() {
            const unmentionedChannels = [];
            // ensure the same mention is not used multiple times if multiple
            // channels have the same name
            const namesIndex = {};
            for (const channel of this.mentionedChannels) {
                const fromIndex = namesIndex[channel.name] !== undefined
                    ? namesIndex[channel.name] + 1 :
                    0;
                const index = this.textInputContent.indexOf(`#${channel.name}`, fromIndex);
                if (index !== -1) {
                    namesIndex[channel.name] = index;
                } else {
                    unmentionedChannels.push(channel);
                }
            }
            return unlink(unmentionedChannels);
        },
        /**
         * @private
         * @returns {string}
         */
        _computePlaceholder() {
            if (!this.thread) {
                return "";
            }
            if (this.thread.model === 'mail.channel') {
                if (this.thread.correspondent) {
                    return sprintf(this.env._t("Message %s..."), this.thread.correspondent.nameOrDisplayName);
                }
                return sprintf(this.env._t("Message #%s..."), this.thread.displayName);
            }
            if (this.isLog) {
                return this.env._t("Log an internal note...");
            }
            return this.env._t("Send a message to followers...");
        },
        /**
         * @private
         * @returns {Partner[]}
         */
        _computeRecipients() {
            const recipients = [...this.mentionedPartners];
            if (this.activeThread && !this.isLog) {
                for (const recipient of this.activeThread.suggestedRecipientInfoList) {
                    if (recipient.partner && recipient.isSelected) {
                        recipients.push(recipient.partner);
                    }
                }
            }
            return replace(recipients);
        },
        /**
         * @private
         */
        _reset() {
            this.update({
                attachments: clear(),
                mentionedChannels: clear(),
                mentionedPartners: clear(),
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
            compute: '_computeActiveThread',
            readonly: true,
            required: true,
        }),
        /**
         * States which attachments are currently being created in this composer.
         */
        attachments: many('Attachment', {
            inverse: 'composer',
        }),
        canPostMessage: attr({
            compute: '_computeCanPostMessage',
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
            compute: '_computeHasUploadingAttachment',
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
            compute: '_computeMentionedChannels',
        }),
        mentionedPartners: many('Partner', {
            compute: '_computeMentionedPartners',
        }),
        messageViewInEditing: one('MessageView', {
            identifying: true,
            inverse: 'composerForEditing',
            readonly: true,
        }),
        /**
         * Placeholder displayed in the composer textarea when it's empty
         */
        placeholder: attr({
            compute: '_computePlaceholder',
        }),
        /**
         * Determines the extra `Partner` (on top of existing followers)
         * that will receive the message being composed by `this`, and that will
         * also be added as follower of `this.activeThread`.
         */
        recipients: many('Partner', {
            compute: '_computeRecipients',
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
            readonly: true,
        }),
    },
});
