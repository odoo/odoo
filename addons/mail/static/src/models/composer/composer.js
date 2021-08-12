/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2one, one2many } from '@mail/model/model_field';
import { clear, insert, link, replace, unlink, unlinkAll } from '@mail/model/model_field_command';
import {
    isEventHandled,
    markEventHandled,
} from '@mail/utils/utils';
import {
    addLink,
    escapeAndCompactTextContent,
    parseAndTransform,
} from '@mail/js/utils';

function factory(dependencies) {

    class Composer extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            this.onClickAddAttachment = this.onClickAddAttachment.bind(this);
            this.onClickDiscard = this.onClickDiscard.bind(this);
            this.onClickFullComposer = this.onClickFullComposer.bind(this);
            this.onClickSend = this.onClickSend.bind(this);
            this.onComposerSuggestionClicked = this.onComposerSuggestionClicked.bind(this);
            this.onComposerTextInputSendShortcut = this.onComposerTextInputSendShortcut.bind(this);
            this.onEmojiSelection = this.onEmojiSelection.bind(this);
            this.onKeydown = this.onKeydown.bind(this);
            this.onKeydownEmojiButton = this.onKeydownEmojiButton.bind(this);
            this.onPasteTextInput = this.onPasteTextInput.bind(this);
        }

        /**
         * @override
         */
        _willCreate() {
            const res = super._willCreate(...arguments);
            /**
             * Determines whether there is a mention RPC currently in progress.
             * Useful to queue a new call if there is already one pending.
             */
            this._hasMentionRpcInProgress = false;
            /**
             * Determines the next function to execute after the current mention
             * RPC is done, if any.
             */
            this._nextMentionRpcFunction = undefined;
            return res;
        }

        /**
         * @override
         */
        _willDelete() {
            // Clears the mention queue on deleting the record to prevent
            // unnecessary RPC.
            this._nextMentionRpcFunction = undefined;
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Closes the suggestion list.
         */
        closeSuggestions() {
            this.update({ suggestionDelimiterPosition: clear() });
        }

        /**
         * Hides the composer, which only makes sense if the composer is
         * currently used as a Discuss Inbox reply composer.
         */
        discard() {
            if (this.discussAsReplying) {
                this.discussAsReplying.clearReplyingToMessage();
            }
        }

        /**
         * Focus this composer and remove focus from all others.
         * Focus is a global concern, it makes no sense to have multiple composers focused at the
         * same time.
         */
        focus() {
            const allComposers = this.messaging.models['mail.composer'].all();
            for (const otherComposer of allComposers) {
                if (otherComposer !== this && otherComposer.hasFocus) {
                    otherComposer.update({ hasFocus: false });
                }
            }
            this.update({ hasFocus: true });
            if (this.messaging.device.isMobile && this.component) {
                this.component.el.scrollIntoView();
            }
            if (this.textInputRef) {
                this.textInputRef.comp.focus();
            }
        }

        /**
         * Inserts text content in text input based on selection.
         *
         * @param {string} content
         */
        insertIntoTextInput(content) {
            const partA = this.textInputContent.slice(0, this.textInputCursorStart);
            const partB = this.textInputContent.slice(
                this.textInputCursorEnd,
                this.textInputContent.length
            );
            let suggestionDelimiterPosition = this.suggestionDelimiterPosition;
            if (
                suggestionDelimiterPosition !== undefined &&
                suggestionDelimiterPosition >= this.textInputCursorStart
            ) {
                suggestionDelimiterPosition = suggestionDelimiterPosition + content.length;
            }
            this.update({
                isLastStateChangeProgrammatic: true,
                suggestionDelimiterPosition,
                textInputContent: partA + content + partB,
                textInputCursorEnd: this.textInputCursorStart + content.length,
                textInputCursorStart: this.textInputCursorStart + content.length,
            });
        }

        insertSuggestion() {
            const cursorPosition = this.textInputCursorStart;
            let textLeft = this.textInputContent.substring(
                0,
                this.suggestionDelimiterPosition + 1
            );
            let textRight = this.textInputContent.substring(
                cursorPosition,
                this.textInputContent.length
            );
            if (this.suggestionDelimiter === ':') {
                textLeft = this.textInputContent.substring(
                    0,
                    this.suggestionDelimiterPosition
                );
                textRight = this.textInputContent.substring(
                    cursorPosition,
                    this.textInputContent.length
                );
            }
            const recordReplacement = this.activeSuggestedRecord.getMentionText();
            const updateData = {
                isLastStateChangeProgrammatic: true,
                textInputContent: textLeft + recordReplacement + ' ' + textRight,
                textInputCursorEnd: textLeft.length + recordReplacement.length + 1,
                textInputCursorStart: textLeft.length + recordReplacement.length + 1,
            };
            // Specific cases for channel and partner mentions: the message with
            // the mention will appear in the target channel, or be notified to
            // the target partner.
            switch (this.activeSuggestedRecord.constructor.modelName) {
                case 'mail.thread':
                    Object.assign(updateData, { mentionedChannels: link(this.activeSuggestedRecord) });
                    break;
                case 'mail.partner':
                    Object.assign(updateData, { mentionedPartners: link(this.activeSuggestedRecord) });
                    break;
            }
            this.update(updateData);
        }

        /**
         * @private
         * @returns {mail.partner[]}
         */
        _computeRecipients() {
            const recipients = [...this.mentionedPartners];
            if (this.thread && !this.isLog) {
                for (const recipient of this.thread.suggestedRecipientInfoList) {
                    if (recipient.partner && recipient.isSelected) {
                        recipients.push(recipient.partner);
                    }
                }
            }
            return replace(recipients);
        }

        /**
         * Open the full composer modal.
         */
        async openFullComposer() {
            const attachmentIds = this.attachments.map(attachment => attachment.id);

            const context = {
                default_attachment_ids: attachmentIds,
                default_body: escapeAndCompactTextContent(this.textInputContent),
                default_is_log: this.isLog,
                default_model: this.thread.model,
                default_partner_ids: this.recipients.map(partner => partner.id),
                default_res_id: this.thread.id,
                mail_post_autofollow: true,
            };

            const action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: context,
            };
            const options = {
                on_close: () => {
                    if (!this.exists()) {
                        return;
                    }
                    this._reset();
                    this.thread.loadNewMessages();
                },
            };
            await this.env.bus.trigger('do-action', { action, options });
        }

        /**
         * Post a message in provided composer's thread based on current composer fields values.
         */
        async postMessage() {
            if (!this.canPostMessage) {
                if (this.hasUploadingAttachment) {
                    this.env.services['notification'].notify({
                        message: this.env._t("Please wait while the file is uploading."),
                        type: 'warning',
                    });
                }
                return;
            }
            const thread = this.thread;
            this.thread.unregisterCurrentPartnerIsTyping({ immediateNotify: true });
            const escapedAndCompactContent = escapeAndCompactTextContent(this.textInputContent);
            let body = escapedAndCompactContent.replace(/&nbsp;/g, ' ').trim();
            // This message will be received from the mail composer as html content
            // subtype but the urls will not be linkified. If the mail composer
            // takes the responsibility to linkify the urls we end up with double
            // linkification a bit everywhere. Ideally we want to keep the content
            // as text internally and only make html enrichment at display time but
            // the current design makes this quite hard to do.
            body = this._generateMentionsLinks(body);
            body = parseAndTransform(body, addLink);
            body = this._generateEmojisOnHtml(body);
            let postData = {
                attachment_ids: this.attachments.map(attachment => attachment.id),
                body,
                message_type: 'comment',
                partner_ids: this.recipients.map(partner => partner.id),
            };
            try {
                let messageId;
                this.update({ isPostingMessage: true });
                if (thread.model === 'mail.channel') {
                    const command = this._getCommandFromText(body);
                    Object.assign(postData, {
                        subtype_xmlid: 'mail.mt_comment',
                    });
                    if (command) {
                        command.execute({ channel: thread, postData });
                    } else {
                        messageId = await this.async(() =>
                            this.messaging.models['mail.thread'].performRpcMessagePost({
                                postData,
                                threadId: thread.id,
                                threadModel: thread.model,
                            })
                        );
                    }
                } else {
                    Object.assign(postData, {
                        subtype_xmlid: this.isLog ? 'mail.mt_note' : 'mail.mt_comment',
                    });
                    if (!this.isLog) {
                        postData.context = {
                            mail_post_autofollow: true,
                        };
                    }
                    messageId = await this.async(() =>
                        this.messaging.models['mail.thread'].performRpcMessagePost({
                            postData,
                            threadId: thread.id,
                            threadModel: thread.model,
                        })
                    );
                    const [messageData] = await this.async(() => this.env.services.rpc({
                        model: 'mail.message',
                        method: 'message_format',
                        args: [[messageId]],
                    }, { shadow: true }));
                    this.messaging.models['mail.message'].insert(Object.assign(
                        {},
                        this.messaging.models['mail.message'].convertData(messageData),
                        {
                            originThread: insert({
                                id: thread.id,
                                model: thread.model,
                            }),
                        })
                    );
                    thread.loadNewMessages();
                }
                for (const threadView of this.thread.threadViews) {
                    // Reset auto scroll to be able to see the newly posted message.
                    threadView.update({ hasAutoScrollOnMessageReceived: true });
                }
                thread.refreshFollowers();
                thread.fetchAndUpdateSuggestedRecipients();
                this._reset();
            } finally {
                this.update({ isPostingMessage: false });
                if (this.component) {
                    this.component.trigger('o-message-posted');
                }
            }
        }

        /**
         * Called when current partner is inserting some input in composer.
         * Useful to notify current partner is currently typing something in the
         * composer of this thread to all other members.
         */
        handleCurrentPartnerIsTyping() {
            if (!this.thread) {
                return;
            }
            if (
                this.suggestionModelName === 'mail.channel_command' ||
                this._getCommandFromText(this.textInputContent)
            ) {
                return;
            }
            if (this.thread.typingMembers.includes(this.messaging.currentPartner)) {
                this.thread.refreshCurrentPartnerIsTyping();
            } else {
                this.thread.registerCurrentPartnerIsTyping();
            }
        }

        /**
         * Called when clicking on attachment button.
         */
        onClickAddAttachment() {
            this.fileUploaderRef.comp.openBrowserFileUploader();
            if (!this.messaging.device.isMobile) {
                this.focus();
            }
        }

        /**
         * Called when clicking on "expand" button.
         */
        onClickFullComposer() {
            this.openFullComposer();
        }

        /**
         * Called when clicking on "discard" button.
         *
         * @param {MouseEvent} ev
         */
        onClickDiscard(ev) {
            this.discard();
        }

        /**
         * Called when clicking on "send" button.
         */
        async onClickSend() {
            await this.postMessage();
            this.focus();
        }

        /**
         * Handles composer send shortcut.
         */
        onComposerTextInputSendShortcut() {
            this.postMessage();
        }

        /**
         * Handle onComposerSuggestionClicked event
         */
        onComposerSuggestionClicked() {
            this.focus();
        }

        /**
         * Called when selection an emoji from the emoji popover (from the emoji
         * button).
         *
         * @param {CustomEvent} ev
         * @param {Object} ev.detail
         * @param {string} ev.detail.unicode
         */
        onEmojiSelection(ev) {
            ev.stopPropagation();
            this.textInputRef.comp.saveStateInStore();
            this.insertIntoTextInput(ev.detail.unicode);
            if (!this.messaging.device.isMobile) {
                this.focus();
            }
        }

        /**
         * Handles keydown on the composer.
         *
         * @param {KeyboardEvent} ev
         */
        onKeydown(ev) {
            if (ev.key === 'Escape') {
                if (isEventHandled(ev, 'ComposerTextInput.closeSuggestions')) {
                    return;
                }
                if (isEventHandled(ev, 'Composer.closeEmojisPopover')) {
                    return;
                }
                ev.preventDefault();
                this.discard();
            }
        }

        /**
         * Handles keydown on emoji button.
         *
         * @param {KeyboardEvent} ev
         */
        onKeydownEmojiButton(ev) {
            if (ev.key === 'Escape') {
                if (this.emojisPopoverRef.comp) {
                    this.emojisPopoverRef.comp.close();
                    this.focus();
                    markEventHandled(ev, 'Composer.closeEmojisPopover');
                }
            }
        }

        /**
         * Handles paste on composer text input.
         *
         * @param {CustomEvent} ev
         */
        async onPasteTextInput(ev) {
            if (!ev.clipboardData || !ev.clipboardData.files) {
                return;
            }
            await this.fileUploaderRef.comp.uploadFiles(ev.clipboardData.files);
        }

        /**
         * Sets the first suggestion as active. Main and extra records are
         * considered together.
         */
        setFirstSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const firstRecord = suggestedRecords[0];
            this.update({ activeSuggestedRecord: link(firstRecord) });
        }

        /**
         * Sets the last suggestion as active. Main and extra records are
         * considered together.
         */
        setLastSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const { length, [length - 1]: lastRecord } = suggestedRecords;
            this.update({ activeSuggestedRecord: link(lastRecord) });
        }

        /**
         * Sets the next suggestion as active. Main and extra records are
         * considered together.
         */
        setNextSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const activeElementIndex = suggestedRecords.findIndex(
                suggestion => suggestion === this.activeSuggestedRecord
            );
            if (activeElementIndex === suggestedRecords.length - 1) {
                // loop when reaching the end of the list
                this.setFirstSuggestionActive();
                return;
            }
            const nextRecord = suggestedRecords[activeElementIndex + 1];
            this.update({ activeSuggestedRecord: link(nextRecord) });
        }

        /**
         * Sets the previous suggestion as active. Main and extra records are
         * considered together.
         */
        setPreviousSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const activeElementIndex = suggestedRecords.findIndex(
                suggestion => suggestion === this.activeSuggestedRecord
            );
            if (activeElementIndex === 0) {
                // loop when reaching the start of the list
                this.setLastSuggestionActive();
                return;
            }
            const previousRecord = suggestedRecords[activeElementIndex - 1];
            this.update({ activeSuggestedRecord: link(previousRecord) });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.thread}
         */
        _computeActiveThread() {
            if (this.messageViewInEditing && this.messageViewInEditing.message && this.messageViewInEditing.message.originThread) {
                return replace(this.messageViewInEditing.message.originThread);
            }
            if (this.thread) {
                return replace(this.thread);
            }
            return clear();
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeCanPostMessage() {
            if (this.thread && !this.textInputContent && this.attachments.length === 0) {
                return false;
            }
            return !this.hasUploadingAttachment && !this.isPostingMessage;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasUploadingAttachment() {
            return this.attachments.some(attachment => attachment.isUploading);
        }

        /**
         * Detects if mentioned partners are still in the composer text input content
         * and removes them if not.
         *
         * @private
         * @returns {mail.partner[]}
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
        }

        /**
         * Detects if mentioned channels are still in the composer text input content
         * and removes them if not.
         *
         * @private
         * @returns {mail.partner[]}
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
        }

        /**
         * @private
         * @returns {mail.partner[]}
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
        }

        /**
         * @private
         */
        _reset() {
            this.update({
                attachments: clear(),
                isLastStateChangeProgrammatic: true,
                mentionedChannels: clear(),
                mentionedPartners: clear(),
                textInputContent: clear(),
                textInputCursorEnd: clear(),
                textInputCursorStart: clear(),
                textInputSelectionDirection: clear(),
            });
        }

    }

    Composer.fields = {
        activeThread: many2one('mail.thread', {
            compute: '_computeActiveThread',
            readonly: true,
            required: true,
        }),
        /**
         * States which attachments are currently being created in this composer.
         */
        attachments: one2many('mail.attachment', {
            inverse: 'composer',
        }),
        canPostMessage: attr({
            compute: '_computeCanPostMessage',
            default: false,
        }),
        composerViews: one2many('mail.composer_view', {
            inverse: 'composer',
            isCausal: true,
        }),
        /**
         * States the OWL component of this composer.
         */
        component: attr(),
        /**
         * States the OWL ref of the "fileUploader".
         */
        fileUploaderRef: attr(),
        /**
         * This field determines whether some attachments linked to this
         * composer are being uploaded.
         */
        hasUploadingAttachment: attr({
            compute: '_computeHasUploadingAttachment',
        }),
        /**
         * Determines whether the last change (since the last render) was
         * programmatic. Useful to avoid restoring the state when its change was
         * from a user action, in particular to prevent the cursor from jumping
         * to its previous position after the user clicked on the textarea while
         * it didn't have the focus anymore.
         */
        isLastStateChangeProgrammatic: attr({
            default: false,
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
        mentionedChannels: many2many('mail.thread', {
            compute: '_computeMentionedChannels',
        }),
        mentionedPartners: many2many('mail.partner', {
            compute: '_computeMentionedPartners',
        }),
        messageViewInEditing: one2one('mail.message_view', {
            inverse: 'composerForEditing',
            readonly: true,
        }),
        /**
         * Determines the extra `mail.partner` (on top of existing followers)
         * that will receive the message being composed by `this`, and that will
         * also be added as follower of `this.activeThread`.
         */
        recipients: many2many('mail.partner', {
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
        /**
         * States the OWL ref of the "fileUploader".
         */
        textInputRef: attr(),
        textInputSelectionDirection: attr({
            default: "none",
        }),
        /**
         * States the thread which this composer represents the state (if any).
         */
        thread: one2one('mail.thread', {
            inverse: 'composer',
            readonly: true,
        }),
    };
    Composer.identifyingFields = [['thread', 'messageViewInEditing']];
    Composer.modelName = 'mail.composer';

    return Composer;
}

registerNewModel('mail.composer', factory);
