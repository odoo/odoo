/** @odoo-module **/

import { emojis } from '@mail/js/emojis';
import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, replace, unlink, unlinkAll } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';
import { addLink, escapeAndCompactTextContent, parseAndTransform } from '@mail/js/utils';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

const { escape } = owl;

registerModel({
    name: 'ComposerView',
    identifyingFields: [['threadView', 'messageViewInEditing', 'chatter']],
    lifecycleHooks: {
        _willCreate() {
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
        },
        _created() {
            document.addEventListener('click', this.onClickCaptureGlobal, true);
        },
        _willDelete() {
            // Clears the mention queue on deleting the record to prevent
            // unnecessary RPC.
            this._nextMentionRpcFunction = undefined;
            document.removeEventListener('click', this.onClickCaptureGlobal, true);
        },
    },
    recordMethods: {
        /**
         * Closes the suggestion list.
         */
        closeSuggestions() {
            this.update({ suggestionDelimiterPosition: clear() });
        },
        /**
         * Returns whether the given html element is inside this composer view,
         * including whether it's inside the emoji popover when active.
         *
         * @param {Element} element
         * @returns {boolean}
         */
        contains(element) {
            // emoji popover is outside but should be considered inside
            if (this.emojisPopoverView && this.emojisPopoverView.contains(element)) {
                return true;
            }
            return Boolean(this.component && this.component.root.el && this.component.root.el.contains(element));
        },
        /**
         * Hides the composer, which only makes sense if the composer is
         * currently used as a Discuss Inbox reply composer or as message
         * editing.
         */
        discard() {
            if (this.messageViewInEditing) {
                this.messageViewInEditing.stopEditing();
            }
            if (this.threadView && this.threadView.replyingToMessageView) {
                const { threadView } = this;
                if (this.threadView.thread === this.messaging.inbox) {
                    this.delete();
                }
                threadView.update({ replyingToMessageView: clear() });
            }
        },
        /**
         * Called when current partner is inserting some input in composer.
         * Useful to notify current partner is currently typing something in the
         * composer of this thread to all other members.
         */
        handleCurrentPartnerIsTyping() {
            if (!this.composer.thread) {
                return; // not supported for non-thread composer (eg. messaging editing)
            }
            if (this.messaging.isCurrentUserGuest) {
                return; // not supported for guests
            }
            if (
                this.suggestionModelName === 'ChannelCommand' ||
                this._getCommandFromText(this.composer.textInputContent)
            ) {
                return;
            }
            if (this.composer.thread.typingMembers.includes(this.messaging.currentPartner)) {
                this.composer.thread.refreshCurrentPartnerIsTyping();
            } else {
                this.composer.thread.registerCurrentPartnerIsTyping();
            }
        },
        /**
         * Inserts text content in text input based on selection.
         *
         * @param {string} content
         */
        insertIntoTextInput(content) {
            const partA = this.composer.textInputContent.slice(0, this.composer.textInputCursorStart);
            const partB = this.composer.textInputContent.slice(
                this.composer.textInputCursorEnd,
                this.composer.textInputContent.length
            );
            let suggestionDelimiterPosition = this.suggestionDelimiterPosition;
            if (
                suggestionDelimiterPosition !== undefined &&
                suggestionDelimiterPosition >= this.composer.textInputCursorStart
            ) {
                suggestionDelimiterPosition = suggestionDelimiterPosition + content.length;
            }
            this.composer.update({
                isLastStateChangeProgrammatic: true,
                textInputContent: partA + content + partB,
                textInputCursorEnd: this.composer.textInputCursorStart + content.length,
                textInputCursorStart: this.composer.textInputCursorStart + content.length,
            });
            this.update({ suggestionDelimiterPosition });
        },
        /**
         * Inserts the active suggestion at the current cursor position.
         */
        insertSuggestion() {
            const cursorPosition = this.composer.textInputCursorStart;
            let textLeft = this.composer.textInputContent.substring(
                0,
                this.suggestionDelimiterPosition + 1
            );
            let textRight = this.composer.textInputContent.substring(
                cursorPosition,
                this.composer.textInputContent.length
            );
            if (this.suggestionDelimiter === ':') {
                textLeft = this.composer.textInputContent.substring(
                    0,
                    this.suggestionDelimiterPosition
                );
                textRight = this.composer.textInputContent.substring(
                    cursorPosition,
                    this.composer.textInputContent.length
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
            switch (this.activeSuggestedRecord.constructor.name) {
                case 'Thread':
                    Object.assign(updateData, { mentionedChannels: link(this.activeSuggestedRecord) });
                    break;
                case 'Partner':
                    Object.assign(updateData, { mentionedPartners: link(this.activeSuggestedRecord) });
                    break;
            }
            this.composer.update(updateData);
        },
        /**
         * Handles click on the emojis button.
         */
        onClickButtonEmojis() {
            if (!this.emojisPopoverView) {
                this.update({ emojisPopoverView: insertAndReplace() });
            } else {
                this.update({ emojisPopoverView: clear() });
            }
        },
        /**
         * Handles click on the cancel link.
         *
         * @param {MouseEvent} ev
         */
        onClickCancelLink(ev) {
            ev.preventDefault();
            this.discard();
        },
        /**
         * Discards the composer when clicking away.
         *
         * @private
         * @param {MouseEvent} ev
         */
        async onClickCaptureGlobal(ev) {
            if (this.contains(ev.target)) {
                return;
            }
            // Let event be handled by bubbling handlers first
            await new Promise(this.messaging.browser.setTimeout);
            if (isEventHandled(ev, 'MessageActionList.replyTo')) {
                return;
            }
            this.discard();
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        onClickEmoji(ev) {
            if (this.textInputComponent) {
                this.textInputComponent.saveStateInStore();
            }
            this.insertIntoTextInput(ev.currentTarget.dataset.unicode);
            if (!this.messaging.device.isMobileDevice) {
                this.update({ doFocus: true });
            }
            this.update({ emojisPopoverView: clear() });
        },
        /**
         * Handles click on the save link.
         *
         * @param {MouseEvent} ev
         */
        onClickSaveLink(ev) {
            ev.preventDefault();
            if (!this.composer.canPostMessage) {
                if (this.composer.hasUploadingAttachment) {
                    this.env.services['notification'].notify({
                        message: this.env._t("Please wait while the file is uploading."),
                        type: 'warning',
                    });
                }
                return;
            }
            if (this.messageViewInEditing) {
                this.updateMessage();
                return;
            }
            this.postMessage();
        },
        /**
         * Handles click on the "stop replying" button.
         *
         * @param {MouseEvent} ev
         */
        onClickStopReplying(ev) {
            this.threadView.update({
                replyingToMessageView: clear(),
            });
        },
        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        onKeydownButtonEmojis(ev) {
            if (ev.key === 'Escape' && this.emojisPopoverView) {
                this.update({
                    doFocus: true,
                    emojisPopoverView: clear(),
                });
                markEventHandled(ev, 'Composer.closeEmojisPopover');
            }
        },
        /**
         * Open the full composer modal.
         */
        async openFullComposer() {
            const attachmentIds = this.composer.attachments.map(attachment => attachment.id);
            const context = {
                default_attachment_ids: attachmentIds,
                default_body: escapeAndCompactTextContent(this.composer.textInputContent),
                default_is_log: this.composer.isLog,
                default_model: this.composer.activeThread.model,
                default_partner_ids: this.composer.recipients.map(partner => partner.id),
                default_res_id: this.composer.activeThread.id,
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
            const composer = this.composer;
            const options = {
                on_close: () => {
                    if (!composer.exists()) {
                        return;
                    }
                    composer._reset();
                    if (composer.activeThread) {
                        composer.activeThread.fetchData(['messages']);
                    }
                },
            };
            await this.env.bus.trigger('do-action', { action, options });
        },
        /**
         * Post a message in provided composer's thread based on current composer fields values.
         */
        async postMessage() {
            const composer = this.composer;
            if (composer.thread.model === 'mail.channel') {
                const command = this._getCommandFromText(composer.textInputContent);
                if (command) {
                    await command.execute({ channel: composer.thread, body: composer.textInputContent });
                    if (composer.exists()) {
                        composer._reset();
                    }
                    return;
                }
            }
            if (this.messaging.currentPartner) {
                composer.thread.unregisterCurrentPartnerIsTyping({ immediateNotify: true });
            }
            const postData = this._getMessageData();
            const params = {
                'post_data': postData,
                'thread_id': composer.thread.id,
                'thread_model': composer.thread.model,
            };
            try {
                composer.update({ isPostingMessage: true });
                if (composer.thread.model === 'mail.channel') {
                    Object.assign(postData, {
                        subtype_xmlid: 'mail.mt_comment',
                    });
                } else {
                    Object.assign(postData, {
                        subtype_xmlid: composer.isLog ? 'mail.mt_note' : 'mail.mt_comment',
                    });
                    if (!composer.isLog) {
                        params.context = { mail_post_autofollow: true };
                    }
                }
                if (this.threadView && this.threadView.replyingToMessageView && this.threadView.thread !== this.messaging.inbox) {
                    postData.parent_id = this.threadView.replyingToMessageView.message.id;
                }
                const chatter = this.chatter;
                const { threadView = {} } = this;
                const { thread: chatterThread } = this.chatter || {};
                const { thread: threadViewThread } = threadView;
                const messageData = await this.env.services.rpc({ route: `/mail/message/post`, params });
                if (!this.messaging) {
                    return;
                }
                const message = this.messaging.models['Message'].insert(
                    this.messaging.models['Message'].convertData(messageData)
                );
                for (const threadView of message.originThread.threadViews) {
                    // Reset auto scroll to be able to see the newly posted message.
                    threadView.update({ hasAutoScrollOnMessageReceived: true });
                    threadView.addComponentHint('message-posted', { message });
                }
                if (chatter && chatter.exists() && chatter.component) {
                    chatter.component.trigger('o-message-posted');
                }
                if (chatterThread) {
                    if (this.exists()) {
                        this.delete();
                    }
                    if (chatterThread.exists()) {
                        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
                        chatterThread.fetchData(['followers', 'messages', 'suggestedRecipients']);
                    }
                }
                if (threadViewThread) {
                    if (threadViewThread === this.messaging.inbox) {
                        if (this.exists()) {
                            this.delete();
                        }
                        this.env.services['notification'].notify({
                            message: _.str.sprintf(this.env._t(`Message posted on "%s"`), message.originThread.displayName),
                            type: 'info',
                        });
                    }
                    if (threadView && threadView.exists()) {
                        threadView.update({ replyingToMessageView: clear() });
                    }
                }
                if (composer.exists()) {
                    composer._reset();
                }
            } finally {
                if (composer.exists()) {
                    composer.update({ isPostingMessage: false });
                }
            }
        },
        /**
         * Sets the first suggestion as active. Main and extra records are
         * considered together.
         */
        setFirstSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const firstRecord = suggestedRecords[0];
            this.update({ activeSuggestedRecord: link(firstRecord) });
        },
        /**
         * Sets the last suggestion as active. Main and extra records are
         * considered together.
         */
        setLastSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const { length, [length - 1]: lastRecord } = suggestedRecords;
            this.update({ activeSuggestedRecord: link(lastRecord) });
        },
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
        },
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
        },
        /**
         * Update a posted message when the message is ready.
         */
        async updateMessage() {
            const composer = this.composer;
            if (!composer.textInputContent) {
                this.messageViewInEditing.messageActionList.update({ deleteConfirmDialog: insertAndReplace() });
                return;
            }
            const escapedAndCompactContent = escapeAndCompactTextContent(composer.textInputContent);
            let body = escapedAndCompactContent.replace(/&nbsp;/g, ' ').trim();
            body = this._generateMentionsLinks(body);
            body = parseAndTransform(body, addLink);
            body = this._generateEmojisOnHtml(body);
            let data = {
                body: body,
                attachment_ids: composer.attachments.concat(this.messageViewInEditing.message.attachments).map(attachment => attachment.id),
            };
            try {
                composer.update({ isPostingMessage: true });
                const messageViewInEditing = this.messageViewInEditing;
                await messageViewInEditing.message.updateContent(data);
                if (messageViewInEditing.exists()) {
                    messageViewInEditing.stopEditing();
                }
            } finally {
                if (composer.exists()) {
                    composer.update({ isPostingMessage: false });
                }
            }
        },
        /**
         * Clears the active suggested record on closing mentions or adapt it if
         * the active current record is no longer part of the suggestions.
         *
         * @private
         * @returns {Model}
         */
        _computeActiveSuggestedRecord() {
            if (
                this.mainSuggestedRecords.length === 0 &&
                this.extraSuggestedRecords.length === 0
            ) {
                return unlink();
            }
            if (
                this.mainSuggestedRecords.includes(this.activeSuggestedRecord) ||
                this.extraSuggestedRecords.includes(this.activeSuggestedRecord)
            ) {
                return;
            }
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const firstRecord = suggestedRecords[0];
            return link(firstRecord);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeAttachmentList() {
            return (this.composer && this.composer.attachments.length > 0)
                ? insertAndReplace()
                : clear();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeComposer() {
            if (this.threadView) {
                // When replying to a message, always use the composer from that message's thread
                if (this.threadView && this.threadView.replyingToMessageView) {
                    return replace(this.threadView.replyingToMessageView.message.originThread.composer);
                }
                if (this.threadView.thread && this.threadView.thread.composer) {
                    return replace(this.threadView.thread.composer);
                }
            }
            if (this.messageViewInEditing && this.messageViewInEditing.composerForEditing) {
                return replace(this.messageViewInEditing.composerForEditing);
            }
            if (this.chatter && this.chatter.thread && this.chatter.thread.composer) {
                return replace(this.chatter.thread.composer);
            }
            return clear();
        },
        /**
         * Clears the extra suggested record on closing mentions, and ensures
         * the extra list does not contain any element already present in the
         * main list, which is a requirement for the navigation process.
         *
         * @private
         * @returns {Model[]}
         */
        _computeExtraSuggestedRecords() {
            if (this.suggestionDelimiterPosition === undefined) {
                return unlinkAll();
            }
            return unlink(this.mainSuggestedRecords);
        },
        /**
         * @private
         * @return {boolean}
         */
        _computeHasDropZone() {
            return true;
        },
        /**
         * @private
         * @return {boolean}
         */
        _computeHasSuggestions() {
            return this.mainSuggestedRecords.length > 0 || this.extraSuggestedRecords.length > 0;
        },
        /**
         * Clears the main suggested record on closing mentions.
         *
         * @private
         * @returns {Model[]}
         */
        _computeMainSuggestedRecords() {
            if (this.suggestionDelimiterPosition === undefined) {
                return unlinkAll();
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeSendButtonText() {
            if (
                this.composer &&
                this.composer.isLog &&
                this.composer.activeThread &&
                this.composer.activeThread.model !== 'mail.channel'
            ) {
                return this.env._t("Log");
            }
            return this.env._t("Send");
        },
        /**
         * @private
         * @returns {string[]}
         */
         _computeSendShortcuts() {
            if (this.chatter) {
                return ['ctrl-enter', 'meta-enter'];
            }
            if (this.messageViewInEditing) {
                return ['enter'];
            }
            if (this.threadView) {
                if (!this.messaging.device) {
                    return clear();
                }
                // Actually in mobile there is a send button, so we need there 'enter' to allow new
                // line. Hence, we want to use a different shortcut 'ctrl/meta enter' to send for
                // small screen size with a non-mailing channel. Here send will be done on clicking
                // the button or using the 'ctrl/meta enter' shortcut.
                if (
                    this.messaging.device.isMobile ||
                    (
                        this.messaging.discuss.threadView === this.threadView &&
                        this.messaging.discuss.thread === this.messaging.inbox
                    )
                ) {
                    return ['ctrl-enter', 'meta-enter'];
                }
                return ['enter'];
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionDelimiter() {
            if (
                !this.composer ||
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionDelimiterPosition >= this.composer.textInputContent.length
            ) {
                return clear();
            }
            return this.composer.textInputContent[this.suggestionDelimiterPosition];
        },
        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionModelName() {
            switch (this.suggestionDelimiter) {
                case '@':
                    return 'Partner';
                case ':':
                    return 'CannedResponse';
                case '/':
                    return 'ChannelCommand';
                case '#':
                    return 'Thread';
                default:
                    return clear();
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionSearchTerm() {
            if (
                !this.composer ||
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionDelimiterPosition >= this.composer.textInputCursorStart
            ) {
                return clear();
            }
            return this.composer.textInputContent.substring(this.suggestionDelimiterPosition + 1, this.composer.textInputCursorStart);
        },
        /**
         * Executes the given async function, only when the last function
         * executed by this method terminates. If there is already a pending
         * function it is replaced by the new one. This ensures the result of
         * these function come in the same order as the call order, and it also
         * allows to skip obsolete intermediate calls.
         *
         * @private
         * @param {function} func
         */
        async _executeOrQueueFunction(func) {
            if (this._hasMentionRpcInProgress) {
                this._nextMentionRpcFunction = func;
                return;
            }
            this._hasMentionRpcInProgress = true;
            this._nextMentionRpcFunction = undefined;
            await func();
            if (this.exists()) {
                this._hasMentionRpcInProgress = false;
                if (this._nextMentionRpcFunction) {
                    this._executeOrQueueFunction(this._nextMentionRpcFunction);
                }
            }
        },
        /**
         * @private
         * @param {string} htmlString
         * @returns {string}
         */
        _generateEmojisOnHtml(htmlString) {
            for (const emoji of emojis) {
                for (const source of emoji.sources) {
                    const escapedSource = String(source).replace(
                        /([.*+?=^!:${}()|[\]/\\])/g,
                        '\\$1');
                    const regexp = new RegExp(
                        '(\\s|^)(' + escapedSource + ')(?=\\s|$)',
                        'g');
                    htmlString = htmlString.replace(regexp, '$1' + emoji.unicode);
                }
            }
            return htmlString;
        },
        /**
         *
         * Generates the html link related to the mentioned partner
         *
         * @private
         * @param {string} body
         * @returns {string}
         */
        _generateMentionsLinks(body) {
            // List of mention data to insert in the body.
            // Useful to do the final replace after parsing to avoid using the
            // same tag twice if two different mentions have the same name.
            const mentions = [];
            for (const partner of this.composer.mentionedPartners) {
                const placeholder = `@-mention-partner-${partner.id}`;
                const text = `@${escape(partner.name)}`;
                mentions.push({
                    class: 'o_mail_redirect',
                    id: partner.id,
                    model: 'res.partner',
                    placeholder,
                    text,
                });
                body = body.replace(text, placeholder);
            }
            for (const channel of this.composer.mentionedChannels) {
                const placeholder = `#-mention-channel-${channel.id}`;
                const text = `#${escape(channel.name)}`;
                mentions.push({
                    class: 'o_channel_redirect',
                    id: channel.id,
                    model: 'mail.channel',
                    placeholder,
                    text,
                });
                body = body.replace(text, placeholder);
            }
            const baseHREF = this.env.session.url('/web');
            for (const mention of mentions) {
                const href = `href='${baseHREF}#model=${mention.model}&id=${mention.id}'`;
                const attClass = `class='${mention.class}'`;
                const dataOeId = `data-oe-id='${mention.id}'`;
                const dataOeModel = `data-oe-model='${mention.model}'`;
                const target = `target='_blank'`;
                const link = `<a ${href} ${attClass} ${dataOeId} ${dataOeModel} ${target}>${mention.text}</a>`;
                body = body.replace(mention.placeholder, link);
            }
            return body;
        },
        /**
         * @private
         * @param {string} content html content
         * @returns {ChannelCommand|undefined} command, if any in the content
         */
        _getCommandFromText(content) {
            if (content.startsWith('/')) {
                const firstWord = content.substring(1).split(/\s/)[0];
                return this.messaging.commands.find(command => {
                    if (command.name !== firstWord) {
                        return false;
                    }
                    if (command.channel_types) {
                        return command.channel_types.includes(this.composer.thread.channel_type);
                    }
                    return true;
                });
            }
            return undefined;
        },
        /**
         * Gather data for message post.
         *
         * @private
         * @returns {Object}
         */
        _getMessageData() {
            const escapedAndCompactContent = escapeAndCompactTextContent(this.composer.textInputContent);
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
            return {
                attachment_ids: this.composer.attachments.map(attachment => attachment.id),
                body,
                message_type: 'comment',
                partner_ids: this.composer.recipients.map(partner => partner.id),
            };
        },
        /**
         * Handles change of this composer. Useful to reset the state of the
         * composer text input.
         */
        _onChangeComposer() {
            this.composer.update({ isLastStateChangeProgrammatic: true });
        },
        /**
         * @private
         */
        _onChangeDetectSuggestionDelimiterPosition() {
            if (!this.composer) {
                return;
            }
            if (this.composer.textInputCursorStart !== this.composer.textInputCursorEnd) {
                // avoid interfering with multi-char selection
                return this.update({ suggestionDelimiterPosition: clear() });
            }
            const candidatePositions = [];
            // keep the current delimiter if it is still valid
            if (
                this.suggestionDelimiterPosition !== undefined &&
                this.suggestionDelimiterPosition < this.composer.textInputCursorStart
            ) {
                candidatePositions.push(this.suggestionDelimiterPosition);
            }
            // consider the char before the current cursor position if the
            // current delimiter is no longer valid (or if there is none)
            if (this.composer.textInputCursorStart > 0) {
                candidatePositions.push(this.composer.textInputCursorStart - 1);
            }
            const suggestionDelimiters = ['@', ':', '#', '/'];
            for (const candidatePosition of candidatePositions) {
                if (
                    candidatePosition < 0 ||
                    candidatePosition >= this.composer.textInputContent.length
                ) {
                    continue;
                }
                const candidateChar = this.composer.textInputContent[candidatePosition];
                if (candidateChar === '/' && candidatePosition !== 0) {
                    continue;
                }
                if (!suggestionDelimiters.includes(candidateChar)) {
                    continue;
                }
                const charBeforeCandidate = this.composer.textInputContent[candidatePosition - 1];
                if (charBeforeCandidate && !/\s/.test(charBeforeCandidate)) {
                    continue;
                }
                this.update({ suggestionDelimiterPosition: candidatePosition });
                return;
            }
            return this.update({ suggestionDelimiterPosition: clear() });
        },
        /**
         * Updates the suggestion state based on the currently saved composer
         * state (in particular content and cursor position).
         *
         * @private
         */
        _onChangeUpdateSuggestionList() {
            if (this.messaging.isCurrentUserGuest) {
                return;
            }
            // Update the suggestion list immediately for a reactive UX...
            this._updateSuggestionList();
            // ...and then update it again after the server returned data.
            this._executeOrQueueFunction(async () => {
                if (
                    !this.exists() ||
                    this.suggestionDelimiterPosition === undefined ||
                    this.suggestionSearchTerm === undefined ||
                    !this.suggestionModelName
                ) {
                    return; // ignore obsolete call
                }
                const Model = this.messaging.models[this.suggestionModelName];
                const searchTerm = this.suggestionSearchTerm;
                await Model.fetchSuggestions(searchTerm, { thread: this.composer.activeThread });
                if (!this.exists()) {
                    return;
                }
                this._updateSuggestionList();
                if (
                    this.suggestionSearchTerm &&
                    this.suggestionSearchTerm === searchTerm &&
                    this.suggestionModelName &&
                    this.messaging.models[this.suggestionModelName] === Model &&
                    !this.hasSuggestions
                ) {
                    this.closeSuggestions();
                }
            });
        },
        /**
         * Updates the current suggestion list. This method should be called
         * whenever the UI has to be refreshed following change in state.
         *
         * This method should ideally be a compute, but its dependencies are
         * currently too complex to express due to accessing plenty of fields
         * from all records of dynamic models.
         *
         * @private
         */
        _updateSuggestionList() {
            if (
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionSearchTerm === undefined ||
                !this.suggestionModelName
            ) {
                return;
            }
            const Model = this.messaging.models[this.suggestionModelName];
            const [
                mainSuggestedRecords,
                extraSuggestedRecords = [],
            ] = Model.searchSuggestions(this.suggestionSearchTerm, { thread: this.composer.activeThread });
            const sortFunction = Model.getSuggestionSortFunction(this.suggestionSearchTerm, { thread: this.composer.activeThread });
            mainSuggestedRecords.sort(sortFunction);
            extraSuggestedRecords.sort(sortFunction);
            // arbitrary limit to avoid displaying too many elements at once
            // ideally a load more mechanism should be introduced
            const limit = 8;
            mainSuggestedRecords.length = Math.min(mainSuggestedRecords.length, limit);
            extraSuggestedRecords.length = Math.min(extraSuggestedRecords.length, limit - mainSuggestedRecords.length);
            this.update({
                extraSuggestedRecords: replace(extraSuggestedRecords),
                hasToScrollToActiveSuggestion: true,
                mainSuggestedRecords: replace(mainSuggestedRecords),
            });
        },
    },
    fields: {
        /**
         * Determines the suggested record that is currently active. This record
         * is highlighted in the UI and it will be the selected record if the
         * suggestion is confirmed by the user.
         */
        activeSuggestedRecord: one('Model', {
            compute: '_computeActiveSuggestedRecord',
        }),
        /**
         * Determines the attachment list that will be used to display the attachments.
         */
        attachmentList: one('AttachmentList', {
            compute: '_computeAttachmentList',
            inverse: 'composerViewOwner',
            isCausal: true,
            readonly: true,
        }),
        /**
         * States the ref to the html node of the emojis button.
         */
        buttonEmojisRef: attr(),
        /**
         * States the chatter which this composer allows editing (if any).
         */
        chatter: one('Chatter', {
            inverse: 'composerView',
            readonly: true,
        }),
        /**
         * States the OWL component of this composer view.
         */
        component: attr(),
        /**
         * States the composer state that is displayed by this composer view.
         */
        composer: one('Composer', {
            compute: '_computeComposer',
            inverse: 'composerViews',
            required: true,
        }),
        /**
         * Determines whether this composer should be focused at next render.
         */
        doFocus: attr(),
        /**
         * Determines the emojis popover that is active on this composer view.
         */
        emojisPopoverView: one('PopoverView', {
            inverse: 'composerViewOwnerAsEmoji',
            isCausal: true,
        }),
        /**
         * Determines the extra records that are currently suggested.
         * Allows to have different model types of mentions through a dynamic
         * process. 2 arbitrary lists can be provided and the second is defined
         * as "extra".
         */
        extraSuggestedRecords: many('Model', {
            compute: '_computeExtraSuggestedRecords',
        }),
        fileUploader: one('FileUploader', {
            default: insertAndReplace(),
            inverse: 'composerView',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        hasDropZone: attr({
            compute: '_computeHasDropZone',
        }),
        hasFocus: attr({
            default: false,
        }),
        /**
         * States whether there is any result currently found for the current
         * suggestion delimiter and search term, if applicable.
         */
        hasSuggestions: attr({
            compute: '_computeHasSuggestions',
            default: false,
        }),
        /**
         * Determines whether the currently active suggestion should be scrolled
         * into view.
         */
        hasToScrollToActiveSuggestion: attr({
            default: false,
        }),
        /**
         * Determines the main records that are currently suggested.
         * Allows to have different model types of mentions through a dynamic
         * process. 2 arbitrary lists can be provided and the first is defined
         * as "main".
         */
        mainSuggestedRecords: many('Model', {
            compute: '_computeMainSuggestedRecords',
        }),
        /**
         * States the message view on which this composer allows editing (if any).
         */
        messageViewInEditing: one('MessageView', {
            inverse: 'composerViewInEditing',
            readonly: true,
        }),
        /**
         * Determines the label on the send button of this composer view.
         */
        sendButtonText: attr({
            compute: '_computeSendButtonText',
        }),
        /**
         * Keyboard shortcuts from text input to send message.
         * The format is an array of string that can contain 'enter',
         * 'ctrl-enter', and/or 'meta-enter'.
         */
        sendShortcuts: attr({
            compute: '_computeSendShortcuts',
            default: [],
        }),
        /**
         * States which type of suggestion is currently in progress, if any.
         * The value of this field contains the magic char that corresponds to
         * the suggestion currently in progress, and it must be one of these:
         * canned responses (:), channels (#), commands (/) and partners (@)
         */
        suggestionDelimiter: attr({
            compute: '_computeSuggestionDelimiter',
        }),
        /**
         * States the position inside textInputContent of the suggestion
         * delimiter currently in consideration. Useful if the delimiter char
         * appears multiple times in the content.
         * Note: the position is 0 based so it's important to compare to
         * `undefined` when checking for the absence of a value.
         */
        suggestionDelimiterPosition: attr(),
        /**
         * States the target model name of the suggestion currently in progress,
         * if any.
         */
        suggestionModelName: attr({
            compute: '_computeSuggestionModelName',
        }),
        /**
         * States the search term to use for suggestions (if any).
         */
        suggestionSearchTerm: attr({
            compute: '_computeSuggestionSearchTerm',
        }),
        /**
         * States the OWL text input component of this composer view.
         */
        textInputComponent: attr(),
        /**
         * States the thread view on which this composer allows editing (if any).
         */
        threadView: one('ThreadView', {
            inverse: 'composerView',
            readonly: true,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['composer'],
            methodName: '_onChangeComposer',
        }),
        new OnChange({
            dependencies: ['composer.textInputContent', 'composer.textInputCursorEnd', 'composer.textInputCursorStart'],
            methodName: '_onChangeDetectSuggestionDelimiterPosition',
        }),
        new OnChange({
            dependencies: ['suggestionDelimiterPosition', 'suggestionModelName', 'suggestionSearchTerm', 'composer.activeThread'],
            methodName: '_onChangeUpdateSuggestionList',
        }),
    ],
});
