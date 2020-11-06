odoo.define('mail/static/src/models/composer/composer.js', function (require) {
'use strict';

const emojis = require('mail.emojis');
const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2one } = require('mail/static/src/model/model_field.js');
const mailUtils = require('mail.utils');

const {
    addLink,
    escapeAndCompactTextContent,
    parseAndTransform,
} = require('mail.utils');

function factory(dependencies) {

    class Composer extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        closeSuggestions() {
            if (this.activeSuggestedRecordName) {
                this.update({
                    [this.activeSuggestedRecordName]: [['unlink']],
                });
            }
            if (this.extraSuggestedRecordsListName) {
                this.update({
                    [this.extraSuggestedRecordsListName]: [['unlink-all']],
                });
            }
            if (this.mainSuggestedRecordsListName) {
                this.update({
                    [this.mainSuggestedRecordsListName]: [['unlink-all']],
                });
            }
            this.update({
                activeSuggestedRecordName: "",
                extraSuggestedRecordsListName: "",
                mainSuggestedRecordsListName: "",
                suggestionDelimiter: "",
            });
        }

        detectSuggestionDelimiter() {
            const lastInputChar = this.textInputContent.substring(this.textInputCursorStart - 1, this.textInputCursorStart);
            const suggestionDelimiters = ['@', ':', '#', '/'];
            if (suggestionDelimiters.includes(lastInputChar) && !this.hasSuggestions) {
                this.update({ suggestionDelimiter: lastInputChar });
            }
            const mentionKeyword = this._validateMentionKeyword(false);
            if (mentionKeyword !== false) {
                switch (this.suggestionDelimiter) {
                    case '@':
                        this.update({
                            activeSuggestedRecordName: "activeSuggestedPartner",
                            extraSuggestedRecordsListName: "extraSuggestedPartners",
                            mainSuggestedRecordsListName: "mainSuggestedPartners",
                            suggestionModelName: "mail.partner",
                        });
                        this._updateSuggestedPartners(mentionKeyword);
                        break;
                    case ':':
                        this.update({
                            activeSuggestedRecordName: "activeSuggestedCannedResponse",
                            mainSuggestedRecordsListName: "suggestedCannedResponses",
                            suggestionModelName: "mail.canned_response",
                        });
                        this._updateSuggestedCannedResponses(mentionKeyword);
                        break;
                    case '/':
                        this.update({
                            activeSuggestedRecordName: "activeSuggestedChannelCommand",
                            mainSuggestedRecordsListName: "suggestedChannelCommands",
                            suggestionModelName: "mail.channel_command",
                        });
                        this._updateSuggestedChannelCommands(mentionKeyword);
                        break;
                    case '#':
                        this.update({
                            activeSuggestedRecordName: "activeSuggestedChannel",
                            mainSuggestedRecordsListName: "suggestedChannels",
                            suggestionModelName: "mail.thread",
                        });
                        this._updateSuggestedChannels(mentionKeyword);
                        break;
                }
            } else {
                this.closeSuggestions();
            }
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
            this.update({
                textInputContent: partA + content + partB,
                textInputCursorStart: this.textInputCursorStart + content.length,
                textInputCursorEnd: this.textInputCursorStart + content.length,
            });
        }

        insertSuggestion() {
            const cursorPosition = this.textInputCursorStart;
            let textLeft = this.textInputContent.substring(
                0,
                this.textInputContent.substring(0, cursorPosition).lastIndexOf(this.suggestionDelimiter) + 1
            );
            let textRight = this.textInputContent.substring(
                cursorPosition,
                this.textInputContent.length
            );
            if (this.suggestionDelimiter === ':') {
                textLeft = this.textInputContent.substring(
                    0,
                    this.textInputContent.substring(0, cursorPosition).lastIndexOf(this.suggestionDelimiter)
                );
                textRight = this.textInputContent.substring(
                    cursorPosition,
                    this.textInputContent.length
                );
            }
            let recordReplacement = "";
            switch (this.activeSuggestedRecordName) {
                case 'activeSuggestedCannedResponse':
                    recordReplacement = this[this.activeSuggestedRecordName].substitution;
                    break;
                case 'activeSuggestedChannel':
                    recordReplacement = this[this.activeSuggestedRecordName].name;
                    this.update({
                        mentionedChannels: [['link', this[this.activeSuggestedRecordName]]],
                    });
                    break;
                case 'activeSuggestedChannelCommand':
                    recordReplacement = this[this.activeSuggestedRecordName].name;
                    break;
                case 'activeSuggestedPartner':
                    recordReplacement = this[this.activeSuggestedRecordName].name;
                    this.update({
                        mentionedPartners: [['link', this[this.activeSuggestedRecordName]]],
                    });
                    break;
            }
            this.update({
                textInputContent: textLeft + recordReplacement + ' ' + textRight,
                textInputCursorEnd: textLeft.length + recordReplacement.length + 1,
                textInputCursorStart: textLeft.length + recordReplacement.length + 1,
            });
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
                context: {
                    mail_post_autofollow: true,
                },
                message_type: 'comment',
                partner_ids: this.recipients.map(partner => partner.id),
            };
            if (this.subjectContent) {
                postData.subject = this.subjectContent;
            }
            let messageId;
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
            if (this.thread.typingMembers.includes(this.env.messaging.currentPartner)) {
                this.thread.refreshCurrentPartnerIsTyping();
            } else {
                this.thread.registerCurrentPartnerIsTyping();
            }
        }

        setFirstSuggestionActive() {
            if (!this[this.mainSuggestedRecordsListName][0]) {
                if (!this[this.extraSuggestedRecordsListName][0]) {
                    return;
                }
                this.update({
                    [this.activeSuggestedRecordName]: [['link', this[this.extraSuggestedRecordsListName][0]]],
                });
            } else {
                this.update({
                    [this.activeSuggestedRecordName]: [['link', this[this.mainSuggestedRecordsListName][0]]],
                });
            }
        }

        setLastSuggestionActive() {
            if (this[this.extraSuggestedRecordsListName].length === 0) {
                if (this[this.mainSuggestedRecordsListName].length === 0) {
                    return;
                }
                this.update({
                    [this.activeSuggestedRecordName]: [[
                        'link',
                        this[this.mainSuggestedRecordsListName][this[this.mainSuggestedRecordsListName].length - 1]
                    ]],
                });
            }
            this.update({
                [this.activeSuggestedRecordName]: [[
                    'link',
                    this[this.extraSuggestedRecordsListName][this[this.extraSuggestedRecordsListName].length - 1]
                ]],
            });
        }

        setNextSuggestionActive() {
            const fullList = this.extraSuggestedRecordsListName ?
                this[this.mainSuggestedRecordsListName].concat(this[this.extraSuggestedRecordsListName]) :
                this[this.mainSuggestedRecordsListName];
            if (fullList.length === 0) {
                return;
            }
            const activeElementIndex = fullList.findIndex(
                suggestion => suggestion === this[this.activeSuggestedRecordName]
            );
            if (activeElementIndex !== fullList.length - 1) {
                this.update({
                    [this.activeSuggestedRecordName]: [[
                        'link',
                        fullList[activeElementIndex + 1]
                    ]],
                });
            } else {
                this.update({
                    [this.activeSuggestedRecordName]: [['link', fullList[0]]],
                });
            }
        }

        setPreviousSuggestionActive() {
            const fullList = this.extraSuggestedRecordsListName ?
                this[this.mainSuggestedRecordsListName].concat(this[this.extraSuggestedRecordsListName]) :
                this[this.mainSuggestedRecordsListName];
            if (fullList.length === 0) {
                return;
            }
            const activeElementIndex = fullList.findIndex(
                suggestion => suggestion === this[this.activeSuggestedRecordName]
            );
            if (activeElementIndex === -1) {
                this.update({
                    [this.activeSuggestedRecordName]: [['link', fullList[0]]]
                });
            } else if (activeElementIndex !== 0) {
                this.update({
                    [this.activeSuggestedRecordName]: [[
                        'link',
                        fullList[activeElementIndex - 1]
                    ]],
                });
            } else {
                this.update({
                    [this.activeSuggestedRecordName]: [[
                        'link',
                        fullList[fullList.length - 1]
                    ]],
                });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.model}
         */
        _computeActiveSuggestedRecord() {
            return this[this.activeSuggestedRecordName];
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeCanPostMessage() {
            if (!this.textInputContent && this.attachments.length === 0) {
                return false;
            }
            return !this.hasUploadingAttachment;
        }

        /**
         * Ensure extraSuggestedPartners does not contain any partner already
         * present in mainSuggestedPartners. This is necessary for the
         * consistency of suggestion list.
         *
         * @private
         * @returns {mail.partner[]}
         */
        _computeExtraSuggestedPartners() {
            return [['unlink', this.mainSuggestedPartners]];
        }

        /**
         * @private
         * @returns {mail.model[]}
         */
        _computeExtraSuggestedRecordsList() {
            return this.extraSuggestedRecordsListName
                ? this[this.extraSuggestedRecordsListName]
                : [];
        }

        /**
         * @private
         * @return {boolean}
         */
        _computeHasSuggestions() {
            const hasMainSuggestedRecordsList = this.mainSuggestedRecordsListName ? this[this.mainSuggestedRecordsListName].length > 0 : false;
            const hasExtraSuggestedRecordsList = this.extraSuggestedRecordsListName ? this[this.extraSuggestedRecordsListName].length > 0 : false;
            return hasMainSuggestedRecordsList || hasExtraSuggestedRecordsList;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasUploadingAttachment() {
            return this.attachments.some(attachment => attachment.isTemporary);
        }

        /**
         * @private
         * @returns {mail.model[]}
         */
        _computeMainSuggestedRecordsList() {
            return this.mainSuggestedRecordsListName
                ? this[this.mainSuggestedRecordsListName]
                : [];
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
         * @private
         */
        _reset() {
            this.closeSuggestions();
            this.update({
                attachments: [['unlink-all']],
                mentionedChannels: [['unlink-all']],
                mentionedPartners: [['unlink-all']],
                subjectContent: "",
                textInputContent: '',
                textInputCursorEnd: 0,
                textInputCursorStart: 0,
            });
        }

        /**
         * @private
         * @param {string} mentionKeyword
         */
        _updateSuggestedCannedResponses(mentionKeyword) {
            this.update({
                suggestedCannedResponses: [['replace', this.env.messaging.cannedResponses.filter(
                    cannedResponse => cannedResponse.source.includes(mentionKeyword)
                )]],
            });

            if (this.suggestedCannedResponses[0]) {
                this.update({
                    activeSuggestedCannedResponse: [['link', this.suggestedCannedResponses[0]]],
                    hasToScrollToActiveSuggestion: true,
                });
            } else {
                this.update({
                    activeSuggestedCannedResponse: [['unlink']],
                });
            }
        }

        /**
         * @private
         * @param {string} mentionKeyword
         */
        async _updateSuggestedChannels(mentionKeyword) {
            const mentions = await this.async(() => this.env.services.rpc(
                {
                    model: 'mail.channel',
                    method: 'get_mention_suggestions',
                    kwargs: {
                        limit: 8,
                        search: mentionKeyword,
                    },
                },
                { shadow: true }
            ));

            this.update({
                suggestedChannels: [[
                    'insert-and-replace',
                    mentions.map(data => {
                        const threadData = this.env.models['mail.thread'].convertData(data);
                        return Object.assign({ model: 'mail.channel' }, threadData);
                    })
                ]],
            });

            if (this.suggestedChannels[0]) {
                this.update({
                    activeSuggestedChannel: [['link', this.suggestedChannels[0]]],
                    hasToScrollToActiveSuggestion: true,
                });
            } else {
                this.update({
                    activeSuggestedChannel: [['unlink']],
                });
            }
        }

        /**
         * @param {string} mentionKeyword
         */
        _updateSuggestedChannelCommands(mentionKeyword) {
            const commands = this.env.messaging.commands.filter(command => {
                if (!command.name.includes(mentionKeyword)) {
                    return false;
                }
                if (command.channel_types) {
                    return command.channel_types.includes(this.thread.channel_type);
                }
                return true;
            });
            this.update({ suggestedChannelCommands: [['replace', commands]] });
            if (this.suggestedChannelCommands[0]) {
                this.update({
                    activeSuggestedChannelCommand: [['link', this.suggestedChannelCommands[0]]],
                    hasToScrollToActiveSuggestion: true,
                });
            } else {
                this.update({
                    activeSuggestedChannelCommand: [['unlink']],
                });
            }
        }

        /**
         * @private
         * @param {string} mentionKeyword
         */
        async _updateSuggestedPartners(mentionKeyword) {
            const mentions = await this.async(() => this.env.services.rpc(
                {
                    model: 'res.partner',
                    method: 'get_mention_suggestions',
                    kwargs: {
                        limit: 8,
                        search: mentionKeyword,
                    },
                },
                { shadow: true }
            ));

            const mainSuggestedPartners = mentions[0];
            const extraSuggestedPartners = mentions[1];
            this.update({
                extraSuggestedPartners: [[
                    'insert-and-replace',
                    extraSuggestedPartners.map(data =>
                        this.env.models['mail.partner'].convertData(data)
                    )
                ]],
                mainSuggestedPartners: [[
                    'insert-and-replace',
                    mainSuggestedPartners.map(data =>
                        this.env.models['mail.partner'].convertData(data))
                    ]],
            });

            if (this.mainSuggestedPartners[0]) {
                this.update({
                    activeSuggestedPartner: [['link', this.mainSuggestedPartners[0]]],
                    hasToScrollToActiveSuggestion: true,
                });
            } else if (this.extraSuggestedPartners[0]) {
                this.update({
                    activeSuggestedPartner: [['link', this.extraSuggestedPartners[0]]],
                    hasToScrollToActiveSuggestion: true,
                });
            } else {
                this.update({
                    activeSuggestedPartner: [['unlink']],
                });
            }
        }

        /**
         * Validates user's current typing as a correct mention keyword in order
         * to trigger mentions suggestions display.
         * Returns the mention keyword without the suggestion delimiter if it
         * has been validated and false if not.
         *
         * @private
         * @param {boolean} beginningOnly
         * @returns {string|boolean}
         */
        _validateMentionKeyword(beginningOnly) {
            const leftString = this.textInputContent.substring(0, this.textInputCursorStart);

            // use position before suggestion delimiter because there should be whitespaces
            // or line feed/carriage return before the suggestion delimiter
            const beforeSuggestionDelimiterPosition = leftString.lastIndexOf(this.suggestionDelimiter) - 1;
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
        activeSuggestedCannedResponse: many2one('mail.canned_response'),
        activeSuggestedChannel: many2one('mail.thread'),
        activeSuggestedChannelCommand: many2one('mail.channel_command'),
        activeSuggestedPartner: many2one('mail.partner'),
        activeSuggestedRecord: attr({
            compute: '_computeActiveSuggestedRecord',
            dependencies: [
                'activeSuggestedCannedResponse',
                'activeSuggestedChannel',
                'activeSuggestedChannelCommand',
                'activeSuggestedPartner',
                'activeSuggestedRecordName',
            ],
        }),
        activeSuggestedRecordName: attr({
           default: "",
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
        extraSuggestedPartners: many2many('mail.partner', {
            compute: '_computeExtraSuggestedPartners',
            dependencies: [
                'extraSuggestedPartners',
                'mainSuggestedPartners',
            ],
        }),
        extraSuggestedRecordsList: attr({
            compute: '_computeExtraSuggestedRecordsList',
            dependencies: [
                'extraSuggestedPartners',
                'extraSuggestedRecordsListName',
            ],
        }),
        /**
         * Allows to have different model types of mentions through a dynamic process
         * RPC can provide 2 lists and the second is defined as "extra"
         */
        extraSuggestedRecordsListName: attr({
           default: "",
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
        hasSuggestions: attr({
            compute: '_computeHasSuggestions',
            dependencies: [
                'extraSuggestedRecordsListName',
                'extraSuggestedPartners',
                'mainSuggestedRecordsListName',
                'mainSuggestedPartners',
                'suggestedCannedResponses',
                'suggestedChannelCommands',
                'suggestedChannels',
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
         * If true composer will log a note, else a comment will be posted.
         */
        isLog: attr({
            default: false,
        }),
        mainSuggestedRecordsList: attr({
            compute: '_computeMainSuggestedRecordsList',
            dependencies: [
                'mainSuggestedPartners',
                'mainSuggestedRecordsListName',
                'suggestedCannedResponses',
                'suggestedChannelCommands',
                'suggestedChannels',
            ],
        }),
        /**
         * Allows to have different model types of mentions through a dynamic process
         * RPC can provide 2 lists and the first is defined as "main"
         */
        mainSuggestedRecordsListName: attr({
           default: "",
        }),
        mainSuggestedPartners: many2many('mail.partner'),
        mentionedChannels: many2many('mail.thread', {
            compute: '_computeMentionedChannels',
            dependencies: ['textInputContent'],
        }),
        mentionedPartners: many2many('mail.partner', {
            compute: '_computeMentionedPartners',
            dependencies: ['textInputContent'],
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
        suggestedCannedResponses: many2many('mail.canned_response'),
        suggestedChannelCommands: many2many('mail.channel_command'),
        suggestedChannels: many2many('mail.thread'),
        /**
         * Special character used to trigger different kinds of suggestions
         * such as canned responses (:), channels (#), commands (/) and partners (@)
         */
        suggestionDelimiter: attr({
            default: "",
        }),
        suggestionModelName: attr({
           default: "",
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
        thread: one2one('mail.thread', {
            inverse: 'composer',
        }),
    };

    Composer.modelName = 'mail.composer';

    return Composer;
}

registerNewModel('mail.composer', factory);

});
