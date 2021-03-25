odoo.define('mail/static/src/models/composer/composer.js', function (require) {
'use strict';

const emojis = require('mail.emojis');
const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2one } = require('mail/static/src/model/model_field.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const mailUtils = require('mail.utils');

const {
    addLink,
    escapeAndCompactTextContent,
    parseAndTransform,
} = require('mail.utils');

function factory(dependencies) {

    class Composer extends dependencies['mail.model'] {

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
         * @deprecated what this method used to do is now automatically computed
         *  based on composer state
         */
        async detectSuggestionDelimiter() {}

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
            const allComposers = this.env.models['mail.composer'].all();
            for (const otherComposer of allComposers) {
                if (otherComposer !== this && otherComposer.hasFocus) {
                    otherComposer.update({ hasFocus: false });
                }
            }
            this.update({ hasFocus: true });
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
                    Object.assign(updateData, { mentionedChannels: [['link', this.activeSuggestedRecord]] });
                    break;
                case 'mail.partner':
                    Object.assign(updateData, { mentionedPartners: [['link', this.activeSuggestedRecord]] });
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
            return [['replace', recipients]];
        }

        /**
         * Open the full composer modal.
         */
        async openFullComposer() {
            const attachmentIds = this.attachments.map(attachment => attachment.id);

            const context = {
                default_attachment_ids: attachmentIds,
                default_body: mailUtils.escapeAndCompactTextContent(this.textInputContent),
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
                channel_ids: this.mentionedChannels.map(channel => channel.id),
                message_type: 'comment',
                partner_ids: this.recipients.map(partner => partner.id),
            };
            if (this.subjectContent) {
                postData.subject = this.subjectContent;
            }
            try {
                let messageId;
                this.update({ isPostingMessage: true });
                if (thread.model === 'mail.channel') {
                    const command = this._getCommandFromText(body);
                    Object.assign(postData, {
                        subtype_xmlid: 'mail.mt_comment',
                    });
                    if (command) {
                        messageId = await this.async(() => this.env.models['mail.thread'].performRpcExecuteCommand({
                            channelId: thread.id,
                            command: command.name,
                            postData,
                        }));
                    } else {
                        messageId = await this.async(() =>
                            this.env.models['mail.thread'].performRpcMessagePost({
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
                        this.env.models['mail.thread'].performRpcMessagePost({
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
                    this.env.models['mail.message'].insert(Object.assign(
                        {},
                        this.env.models['mail.message'].convertData(messageData),
                        {
                            originThread: [['insert', {
                                id: thread.id,
                                model: thread.model,
                            }]],
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
            if (this.thread.typingMembers.includes(this.env.messaging.currentPartner)) {
                this.thread.refreshCurrentPartnerIsTyping();
            } else {
                this.thread.registerCurrentPartnerIsTyping();
            }
        }

        /**
         * Sets the first suggestion as active. Main and extra records are
         * considered together.
         */
        setFirstSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const firstRecord = suggestedRecords[0];
            this.update({ activeSuggestedRecord: [['link', firstRecord]] });
        }

        /**
         * Sets the last suggestion as active. Main and extra records are
         * considered together.
         */
        setLastSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const { length, [length - 1]: lastRecord } = suggestedRecords;
            this.update({ activeSuggestedRecord: [['link', lastRecord]] });
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
            this.update({ activeSuggestedRecord: [['link', nextRecord]] });
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
            this.update({ activeSuggestedRecord: [['link', previousRecord]] });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @deprecated
         * @private
         * @returns {mail.canned_response}
         */
        _computeActiveSuggestedCannedResponse() {
            if (this.suggestionDelimiter === ':' && this.activeSuggestedRecord) {
                return [['link', this.activeSuggestedRecord]];
            }
            return [['unlink']];
        }

        /**
         * @deprecated
         * @private
         * @returns {mail.thread}
         */
        _computeActiveSuggestedChannel() {
            if (this.suggestionDelimiter === '#' && this.activeSuggestedRecord) {
                return [['link', this.activeSuggestedRecord]];
            }
            return [['unlink']];
        }

        /**
         * @deprecated
         * @private
         * @returns {mail.channel_command}
         */
        _computeActiveSuggestedChannelCommand() {
            if (this.suggestionDelimiter === '/' && this.activeSuggestedRecord) {
                return [['link', this.activeSuggestedRecord]];
            }
            return [['unlink']];
        }

        /**
         * @deprecated
         * @private
         * @returns {mail.partner}
         */
        _computeActiveSuggestedPartner() {
            if (this.suggestionDelimiter === '@' && this.activeSuggestedRecord) {
                return [['link', this.activeSuggestedRecord]];
            }
            return [['unlink']];
        }

        /**
         * Clears the active suggested record on closing mentions or adapt it if
         * the active current record is no longer part of the suggestions.
         *
         * @private
         * @returns {mail.model}
         */
        _computeActiveSuggestedRecord() {
            if (
                this.mainSuggestedRecords.length === 0 &&
                this.extraSuggestedRecords.length === 0
            ) {
                return [['unlink']];
            }
            if (
                this.mainSuggestedRecords.includes(this.activeSuggestedRecord) ||
                this.extraSuggestedRecords.includes(this.activeSuggestedRecord)
            ) {
                return;
            }
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const firstRecord = suggestedRecords[0];
            return [['link', firstRecord]];
        }

        /**
         * @deprecated
         * @private
         * @returns {string}
         */
        _computeActiveSuggestedRecordName() {
            switch (this.suggestionDelimiter) {
                case '@':
                    return "activeSuggestedPartner";
                case ':':
                    return "activeSuggestedCannedResponse";
                case '/':
                    return "activeSuggestedChannelCommand";
                case '#':
                    return "activeSuggestedChannel";
                default:
                    return clear();
            }
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeCanPostMessage() {
            if (!this.textInputContent && this.attachments.length === 0) {
                return false;
            }
            return !this.hasUploadingAttachment && !this.isPostingMessage;
        }

        /**
         * @deprecated
         * @private
         * @returns {mail.partner[]}
         */
        _computeExtraSuggestedPartners() {
            if (this.suggestionDelimiter === '@') {
                return [['replace', this.extraSuggestedRecords]];
            }
            return [['unlink-all']];
        }

        /**
         * Clears the extra suggested record on closing mentions, and ensures
         * the extra list does not contain any element already present in the
         * main list, which is a requirement for the navigation process.
         *
         * @private
         * @returns {mail.model[]}
         */
        _computeExtraSuggestedRecords() {
            if (this.suggestionDelimiterPosition === undefined) {
                return [['unlink-all']];
            }
            return [['unlink', this.mainSuggestedRecords]];
        }

        /**
         * @deprecated
         * @private
         * @returns {mail.model[]}
         */
        _computeExtraSuggestedRecordsList() {
            return this.extraSuggestedRecords;
        }

        /**
         * @deprecated
         * @private
         * @returns {string}
         */
        _computeExtraSuggestedRecordsListName() {
            if (this.suggestionDelimiter === '@') {
                return "extraSuggestedPartners";
            }
            return clear();
        }

        /**
         * @private
         * @return {boolean}
         */
        _computeHasSuggestions() {
            return this.mainSuggestedRecords.length > 0 || this.extraSuggestedRecords.length > 0;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasUploadingAttachment() {
            return this.attachments.some(attachment => attachment.isTemporary);
        }

        /**
         * @deprecated
         * @private
         * @returns {mail.model[]}
         */
        _computeMainSuggestedPartners() {
            if (this.suggestionDelimiter === '@') {
                return [['replace', this.mainSuggestedRecords]];
            }
            return [['unlink-all']];
        }

        /**
         * Clears the main suggested record on closing mentions.
         *
         * @private
         * @returns {mail.model[]}
         */
        _computeMainSuggestedRecords() {
            if (this.suggestionDelimiterPosition === undefined) {
                return [['unlink-all']];
            }
        }

        /**
         * @deprecated
         * @private
         * @returns {mail.model[]}
         */
        _computeMainSuggestedRecordsList() {
            return this.mainSuggestedRecords;
        }

        /**
         * @deprecated
         * @private
         * @returns {string}
         */
        _computeMainSuggestedRecordsListName() {
            switch (this.suggestionDelimiter) {
                case '@':
                    return "mainSuggestedPartners";
                case ':':
                    return "suggestedCannedResponses";
                case '/':
                    return "suggestedChannelCommands";
                case '#':
                    return "suggestedChannels";
                default:
                    return clear();
            }
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
            return [['unlink', unmentionedPartners]];
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
            return [['unlink', unmentionedChannels]];
        }

        /**
         * @deprecated
         * @private
         * @returns {mail.canned_response[]}
         */
        _computeSuggestedCannedResponses() {
            if (this.suggestionDelimiter === ':') {
                return [['replace', this.mainSuggestedRecords]];
            }
            return [['unlink-all']];
        }

        /**
         * @deprecated
         * @private
         * @returns {mail.thread[]}
         */
        _computeSuggestedChannels() {
            if (this.suggestionDelimiter === '#') {
                return [['replace', this.mainSuggestedRecords]];
            }
            return [['unlink-all']];
        }

        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionDelimiter() {
            if (
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionDelimiterPosition >= this.textInputContent.length
            ) {
                return clear();
            }
            return this.textInputContent[this.suggestionDelimiterPosition];
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeSuggestionDelimiterPosition() {
            if (this.textInputCursorStart !== this.textInputCursorEnd) {
                // avoid interfering with multi-char selection
                return clear();
            }
            const candidatePositions = [];
            // keep the current delimiter if it is still valid
            if (
                this.suggestionDelimiterPosition !== undefined &&
                this.suggestionDelimiterPosition < this.textInputCursorStart
            ) {
                candidatePositions.push(this.suggestionDelimiterPosition);
            }
            // consider the char before the current cursor position if the
            // current delimiter is no longer valid (or if there is none)
            if (this.textInputCursorStart > 0) {
                candidatePositions.push(this.textInputCursorStart - 1);
            }
            const suggestionDelimiters = ['@', ':', '#', '/'];
            for (const candidatePosition of candidatePositions) {
                if (
                    candidatePosition < 0 ||
                    candidatePosition >= this.textInputContent.length
                ) {
                    continue;
                }
                const candidateChar = this.textInputContent[candidatePosition];
                if (candidateChar === '/' && candidatePosition !== 0) {
                    continue;
                }
                if (!suggestionDelimiters.includes(candidateChar)) {
                    continue;
                }
                const charBeforeCandidate = this.textInputContent[candidatePosition - 1];
                if (charBeforeCandidate && !/\s/.test(charBeforeCandidate)) {
                    continue;
                }
                return candidatePosition;
            }
            return clear();
        }

        /**
         * @deprecated
         * @private
         * @returns {mail.channel_command[]}
         */
        _computeSuggestedChannelCommands() {
            if (this.suggestionDelimiter === '/') {
                return [['replace', this.mainSuggestedRecords]];
            }
            return [['unlink-all']];
        }

        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionModelName() {
            switch (this.suggestionDelimiter) {
                case '@':
                    return 'mail.partner';
                case ':':
                    return 'mail.canned_response';
                case '/':
                    return 'mail.channel_command';
                case '#':
                    return 'mail.thread';
                default:
                    return clear();
            }
        }

        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionSearchTerm() {
            if (
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionDelimiterPosition >= this.textInputCursorStart
            ) {
                return clear();
            }
            return this.textInputContent.substring(this.suggestionDelimiterPosition + 1, this.textInputCursorStart);
        }

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
            try {
                await this.async(func);
            } finally {
                this._hasMentionRpcInProgress = false;
                if (this._nextMentionRpcFunction) {
                    this._executeOrQueueFunction(this._nextMentionRpcFunction);
                }
            }
        }

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
        }

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
            for (const partner of this.mentionedPartners) {
                const placeholder = `@-mention-partner-${partner.id}`;
                const text = `@${owl.utils.escape(partner.name)}`;
                mentions.push({
                    class: 'o_mail_redirect',
                    id: partner.id,
                    model: 'res.partner',
                    placeholder,
                    text,
                });
                body = body.replace(text, placeholder);
            }
            for (const channel of this.mentionedChannels) {
                const placeholder = `#-mention-channel-${channel.id}`;
                const text = `#${owl.utils.escape(channel.name)}`;
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
        }

        /**
         * @private
         * @param {string} content html content
         * @returns {mail.channel_command|undefined} command, if any in the content
         */
        _getCommandFromText(content) {
            if (content.startsWith('/')) {
                const firstWord = content.substring(1).split(/\s/)[0];
                return this.env.messaging.commands.find(command => {
                    if (command.name !== firstWord) {
                        return false;
                    }
                    if (command.channel_types) {
                        return command.channel_types.includes(this.thread.channel_type);
                    }
                    return true;
                });
            }
            return undefined;
        }

        /**
         * Updates the suggestion state based on the currently saved composer
         * state (in particular content and cursor position).
         *
         * @private
         */
        _onChangeUpdateSuggestionList() {
            // Update the suggestion list immediately for a reactive UX...
            this._updateSuggestionList();
            // ...and then update it again after the server returned data.
            this._executeOrQueueFunction(async () => {
                if (
                    this.suggestionDelimiterPosition === undefined ||
                    this.suggestionSearchTerm === undefined ||
                    !this.suggestionModelName
                ) {
                    // ignore obsolete call
                    return;
                }
                const Model = this.env.models[this.suggestionModelName];
                const searchTerm = this.suggestionSearchTerm;
                await this.async(() => Model.fetchSuggestions(searchTerm, { thread: this.thread }));
                this._updateSuggestionList();
                if (
                    this.suggestionSearchTerm &&
                    this.suggestionSearchTerm === searchTerm &&
                    this.suggestionModelName &&
                    this.env.models[this.suggestionModelName] === Model &&
                    !this.hasSuggestions
                ) {
                    this.closeSuggestions();
                }
            });
        }

        /**
         * @private
         */
        _reset() {
            this.update({
                attachments: [['unlink-all']],
                isLastStateChangeProgrammatic: true,
                mentionedChannels: [['unlink-all']],
                mentionedPartners: [['unlink-all']],
                subjectContent: "",
                textInputContent: '',
                textInputCursorEnd: 0,
                textInputCursorStart: 0,
            });
        }

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
            const Model = this.env.models[this.suggestionModelName];
            const [
                mainSuggestedRecords,
                extraSuggestedRecords = [],
            ] = Model.searchSuggestions(this.suggestionSearchTerm, { thread: this.thread });
            const sortFunction = Model.getSuggestionSortFunction(this.suggestionSearchTerm, { thread: this.thread });
            mainSuggestedRecords.sort(sortFunction);
            extraSuggestedRecords.sort(sortFunction);
            // arbitrary limit to avoid displaying too many elements at once
            // ideally a load more mechanism should be introduced
            const limit = 8;
            mainSuggestedRecords.length = Math.min(mainSuggestedRecords.length, limit);
            extraSuggestedRecords.length = Math.min(extraSuggestedRecords.length, limit - mainSuggestedRecords.length);
            this.update({
                extraSuggestedRecords: [['replace', extraSuggestedRecords]],
                hasToScrollToActiveSuggestion: true,
                mainSuggestedRecords: [['replace', mainSuggestedRecords]],
            });
        }

        /**
         * Validates user's current typing as a correct mention keyword in order
         * to trigger mentions suggestions display.
         * Returns the mention keyword without the suggestion delimiter if it
         * has been validated and false if not.
         *
         * @deprecated
         * @private
         * @param {boolean} beginningOnly
         * @returns {string|boolean}
         */
        _validateMentionKeyword(beginningOnly) {
            // use position before suggestion delimiter because there should be whitespaces
            // or line feed/carriage return before the suggestion delimiter
            const beforeSuggestionDelimiterPosition = this.suggestionDelimiterPosition - 1;
            if (beginningOnly && beforeSuggestionDelimiterPosition > 0) {
                return false;
            }
            let searchStr = this.textInputContent.substring(
                beforeSuggestionDelimiterPosition,
                this.textInputCursorStart
            );
            // regex string start with suggestion delimiter or whitespace then suggestion delimiter
            const pattern = "^" + this.suggestionDelimiter + "|^\\s" + this.suggestionDelimiter;
            const regexStart = new RegExp(pattern, 'g');
            // trim any left whitespaces or the left line feed/ carriage return
            // at the beginning of the string
            searchStr = searchStr.replace(/^\s\s*|^[\n\r]/g, '');
            if (regexStart.test(searchStr) && searchStr.length) {
                searchStr = searchStr.replace(pattern, '');
                return !searchStr.includes(' ') && !/[\r\n]/.test(searchStr)
                    ? searchStr.replace(this.suggestionDelimiter, '')
                    : false;
            }
            return false;
        }
    }

    Composer.fields = {
        /**
         * Deprecated. Use `activeSuggestedRecord` instead.
         */
        activeSuggestedCannedResponse: many2one('mail.canned_response', {
            compute: '_computeActiveSuggestedCannedResponse',
            dependencies: [
                'activeSuggestedRecord',
                'suggestionDelimiter',
            ],
        }),
        /**
         * Deprecated. Use `activeSuggestedRecord` instead.
         */
        activeSuggestedChannel: many2one('mail.thread', {
            compute: '_computeActiveSuggestedChannel',
            dependencies: [
                'activeSuggestedRecord',
                'suggestionDelimiter',
            ],
        }),
        /**
         * Deprecated. Use `activeSuggestedRecord` instead.
         */
        activeSuggestedChannelCommand: many2one('mail.channel_command', {
            compute: '_computeActiveSuggestedChannelCommand',
            dependencies: [
                'activeSuggestedRecord',
                'suggestionDelimiter',
            ],
        }),
        /**
         * Deprecated. Use `activeSuggestedRecord` instead.
         */
        activeSuggestedPartner: many2one('mail.partner', {
            compute: '_computeActiveSuggestedPartner',
            dependencies: [
                'activeSuggestedRecord',
                'suggestionDelimiter',
            ],
        }),
        /**
         * Determines the suggested record that is currently active. This record
         * is highlighted in the UI and it will be the selected record if the
         * suggestion is confirmed by the user.
         */
        activeSuggestedRecord: many2one('mail.model', {
            compute: '_computeActiveSuggestedRecord',
            dependencies: [
                'activeSuggestedRecord',
                'extraSuggestedRecords',
                'mainSuggestedRecords',
            ],
        }),
        /**
         * Deprecated, suggestions should be used in a manner that does not
         * depend on their type. Use `activeSuggestedRecord` directly instead.
         */
        activeSuggestedRecordName: attr({
            compute: '_computeActiveSuggestedRecordName',
            dependencies: [
                'suggestionDelimiter',
            ],
        }),
        attachments: many2many('mail.attachment', {
            inverse: 'composers',
        }),
        /**
         * This field watches the uploading (= temporary) status of attachments
         * linked to this composer.
         *
         * Useful to determine whether there are some attachments that are being
         * uploaded.
         */
        attachmentsAreTemporary: attr({
            related: 'attachments.isTemporary',
        }),
        canPostMessage: attr({
            compute: '_computeCanPostMessage',
            dependencies: [
                'attachments',
                'hasUploadingAttachment',
                'isPostingMessage',
                'textInputContent',
            ],
            default: false,
        }),
        /**
         * Instance of discuss if this composer is used as the reply composer
         * from Inbox. This field is computed from the inverse relation and
         * should be considered read-only.
         */
        discussAsReplying: one2one('mail.discuss', {
            inverse: 'replyingToMessageOriginThreadComposer',
        }),
        /**
         * Deprecated. Use `extraSuggestedRecords` instead.
         */
        extraSuggestedPartners: many2many('mail.partner', {
            compute: '_computeExtraSuggestedPartners',
            dependencies: [
                'extraSuggestedRecords',
                'suggestionDelimiter',
            ],
        }),
        /**
         * Determines the extra records that are currently suggested.
         * Allows to have different model types of mentions through a dynamic
         * process. 2 arbitrary lists can be provided and the second is defined
         * as "extra".
         */
        extraSuggestedRecords: many2many('mail.model', {
            compute: '_computeExtraSuggestedRecords',
            dependencies: [
                'extraSuggestedRecords',
                'mainSuggestedRecords',
                'suggestionDelimiterPosition',
            ],
        }),
        /**
         * Deprecated. Use `extraSuggestedRecords` instead.
         */
        extraSuggestedRecordsList: attr({
            compute: '_computeExtraSuggestedRecordsList',
            dependencies: [
                'extraSuggestedRecords',
            ],
        }),
        /**
         * Deprecated, suggestions should be used in a manner that does not
         * depend on their type. Use `extraSuggestedRecords` directly instead.
         */
        extraSuggestedRecordsListName: attr({
            compute: '_computeExtraSuggestedRecordsListName',
            dependencies: [
                'suggestionDelimiter',
            ],
        }),
        /**
         * This field determines whether some attachments linked to this
         * composer are being uploaded.
         */
        hasUploadingAttachment: attr({
            compute: '_computeHasUploadingAttachment',
            dependencies: [
                'attachments',
                'attachmentsAreTemporary',
            ],
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
            dependencies: [
                'extraSuggestedRecords',
                'mainSuggestedRecords',
            ],
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
            default: false,
        }),
        /**
         * Determines whether a post_message request is currently pending.
         */
        isPostingMessage: attr(),
        /**
         * Deprecated. Use `mainSuggestedRecords` instead.
         */
        mainSuggestedPartners: many2many('mail.partner', {
            compute: '_computeMainSuggestedPartners',
            dependencies: [
                'mainSuggestedRecords',
                'suggestionDelimiter',
            ],
        }),
        /**
         * Determines the main records that are currently suggested.
         * Allows to have different model types of mentions through a dynamic
         * process. 2 arbitrary lists can be provided and the first is defined
         * as "main".
         */
        mainSuggestedRecords: many2many('mail.model', {
            compute: '_computeMainSuggestedRecords',
            dependencies: [
                'mainSuggestedRecords',
                'suggestionDelimiterPosition',
            ],
        }),
        /**
         * Deprecated. Use `mainSuggestedRecords` instead.
         */
        mainSuggestedRecordsList: attr({
            compute: '_computeMainSuggestedRecordsList',
            dependencies: [
                'mainSuggestedRecords',
            ],
        }),
        /**
         * Deprecated, suggestions should be used in a manner that does not
         * depend on their type. Use `mainSuggestedRecords` directly instead.
         */
        mainSuggestedRecordsListName: attr({
            compute: '_computeMainSuggestedRecordsListName',
            dependencies: [
                'suggestionDelimiter',
            ],
        }),
        mentionedChannels: many2many('mail.thread', {
            compute: '_computeMentionedChannels',
            dependencies: ['textInputContent'],
        }),
        mentionedPartners: many2many('mail.partner', {
            compute: '_computeMentionedPartners',
            dependencies: [
                'mentionedPartners',
                'mentionedPartnersName',
                'textInputContent',
            ],
        }),
        /**
         * Serves as compute dependency.
         */
        mentionedPartnersName: attr({
            related: 'mentionedPartners.name',
        }),
        /**
         * Not a real field, used to trigger `_onChangeUpdateSuggestionList`
         * when one of the dependencies changes.
         */
        onChangeUpdateSuggestionList: attr({
            compute: '_onChangeUpdateSuggestionList',
            dependencies: [
                'suggestionDelimiterPosition',
                'suggestionModelName',
                'suggestionSearchTerm',
                'thread',
            ],
        }),
        /**
         * Determines the extra `mail.partner` (on top of existing followers)
         * that will receive the message being composed by `this`, and that will
         * also be added as follower of `this.thread`.
         */
        recipients: many2many('mail.partner', {
            compute: '_computeRecipients',
            dependencies: [
                'isLog',
                'mentionedPartners',
                'threadSuggestedRecipientInfoListIsSelected',
                // FIXME thread.suggestedRecipientInfoList.partner should be a
                // dependency, but it is currently impossible to have a related
                // m2o through a m2m. task-2261221
            ]
        }),
        /**
         * Serves as compute dependency.
         */
        threadSuggestedRecipientInfoList: many2many('mail.suggested_recipient_info', {
            related: 'thread.suggestedRecipientInfoList',
        }),
        /**
         * Serves as compute dependency.
         */
        threadSuggestedRecipientInfoListIsSelected: attr({
            related: 'threadSuggestedRecipientInfoList.isSelected',
        }),
        /**
         * Composer subject input content.
         */
        subjectContent: attr({
            default: "",
        }),
        /**
         * Deprecated. Use `mainSuggestedRecords` instead.
         */
        suggestedCannedResponses: many2many('mail.canned_response', {
            compute: '_computeSuggestedCannedResponses',
            dependencies: [
                'mainSuggestedRecords',
                'suggestionDelimiter',
            ],
        }),
        /**
         * Deprecated. Use `mainSuggestedRecords` instead.
         */
        suggestedChannelCommands: many2many('mail.channel_command', {
            compute: '_computeSuggestedChannelCommands',
            dependencies: [
                'mainSuggestedRecords',
                'suggestionDelimiter',
            ],
        }),
        /**
         * Deprecated. Use `mainSuggestedRecords` instead.
         */
        suggestedChannels: many2many('mail.thread', {
            compute: '_computeSuggestedChannels',
            dependencies: [
                'mainSuggestedRecords',
                'suggestionDelimiter',
            ],
        }),
        /**
         * States which type of suggestion is currently in progress, if any.
         * The value of this field contains the magic char that corresponds to
         * the suggestion currently in progress, and it must be one of these:
         * canned responses (:), channels (#), commands (/) and partners (@)
         */
        suggestionDelimiter: attr({
            compute: '_computeSuggestionDelimiter',
            dependencies: [
                'suggestionDelimiterPosition',
                'textInputContent',
            ],
        }),
        /**
         * States the position inside textInputContent of the suggestion
         * delimiter currently in consideration. Useful if the delimiter char
         * appears multiple times in the content.
         * Note: the position is 0 based so it's important to compare to
         * `undefined` when checking for the absence of a value.
         */
        suggestionDelimiterPosition: attr({
            compute: '_computeSuggestionDelimiterPosition',
            dependencies: [
                'textInputContent',
                'textInputCursorEnd',
                'textInputCursorStart',
            ],
        }),
        /**
         * States the target model name of the suggestion currently in progress,
         * if any.
         */
        suggestionModelName: attr({
            compute: '_computeSuggestionModelName',
            dependencies: [
                'suggestionDelimiter',
            ],
        }),
        /**
         * States the search term to use for suggestions (if any).
         */
        suggestionSearchTerm: attr({
            compute: '_computeSuggestionSearchTerm',
            dependencies: [
                'suggestionDelimiterPosition',
                'textInputContent',
                'textInputCursorStart',
            ],
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
        thread: one2one('mail.thread', {
            inverse: 'composer',
        }),
    };

    Composer.modelName = 'mail.composer';

    return Composer;
}

registerNewModel('mail.composer', factory);

});
