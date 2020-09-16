odoo.define('mail/static/src/models/composer/composer.js', function (require) {
'use strict';

const emojis = require('mail.emojis');
const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const { attr, many2many, many2one, one2one } = require('mail/static/src/model/model_field_utils.js');
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
            if (this.__mfield_activeSuggestedRecordName(this)) {
                this.update({
                    [this.__mfield_activeSuggestedRecordName(this)]: [['unlink']],
                });
            }
            if (this.__mfield_extraSuggestedRecordsListName(this)) {
                this.update({
                    [this.__mfield_extraSuggestedRecordsListName(this)]: [['unlink-all']],
                });
            }
            if (this.__mfield_mainSuggestedRecordsListName(this)) {
                this.update({
                    [this.__mfield_mainSuggestedRecordsListName(this)]: [['unlink-all']],
                });
            }
            this.update({
                __mfield_activeSuggestedRecordName: clear(),
                __mfield_extraSuggestedRecordsListName: "",
                __mfield_mainSuggestedRecordsListName: "",
                __mfield_suggestionDelimiter: "",
            });
        }

        detectSuggestionDelimiter() {
            const lastInputChar = this.__mfield_textInputContent(this).substring(this.__mfield_textInputCursorStart(this) - 1, this.__mfield_textInputCursorStart(this));
            const suggestionDelimiters = ['@', ':', '#', '/'];
            if (suggestionDelimiters.includes(lastInputChar) && !this.__mfield_hasSuggestions(this)) {
                this.update({ __mfield_suggestionDelimiter: lastInputChar });
            }
            const mentionKeyword = this._validateMentionKeyword(false);
            if (mentionKeyword !== false) {
                switch (this.__mfield_suggestionDelimiter(this)) {
                    case '@':
                        this.update({
                            __mfield_activeSuggestedRecordName: "__mfield_activeSuggestedPartner",
                            __mfield_extraSuggestedRecordsListName: "__mfield_extraSuggestedPartners",
                            __mfield_mainSuggestedRecordsListName: "__mfield_mainSuggestedPartners",
                            __mfield_suggestionModelName: "mail.partner",
                        });
                        this._updateSuggestedPartners(mentionKeyword);
                        break;
                    case ':':
                        this.update({
                            __mfield_activeSuggestedRecordName: "__mfield_activeSuggestedCannedResponse",
                            __mfield_mainSuggestedRecordsListName: "__mfield_suggestedCannedResponses",
                            __mfield_suggestionModelName: "mail.canned_response",
                        });
                        this._updateSuggestedCannedResponses(mentionKeyword);
                        break;
                    case '/':
                        this.update({
                            __mfield_activeSuggestedRecordName: "__mfield_activeSuggestedChannelCommand",
                            __mfield_mainSuggestedRecordsListName: "__mfield_suggestedChannelCommands",
                            __mfield_suggestionModelName: "mail.channel_command",
                        });
                        this._updateSuggestedChannelCommands(mentionKeyword);
                        break;
                    case '#':
                        this.update({
                            __mfield_activeSuggestedRecordName: "__mfield_activeSuggestedChannel",
                            __mfield_mainSuggestedRecordsListName: "__mfield_suggestedChannels",
                            __mfield_suggestionModelName: "mail.thread",
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
            if (this.__mfield_discussAsReplying(this)) {
                this.__mfield_discussAsReplying(this).clearReplyingToMessage();
            }
        }

        /**
         * Inserts text content in text input based on selection.
         *
         * @param {string} content
         */
        insertIntoTextInput(content) {
            const partA = this.__mfield_textInputContent(this).slice(0, this.__mfield_textInputCursorStart(this));
            const partB = this.__mfield_textInputContent(this).slice(
                this.__mfield_textInputCursorEnd(this),
                this.__mfield_textInputContent(this).length
            );
            this.update({
                __mfield_textInputContent: partA + content + partB,
                __mfield_textInputCursorStart: this.__mfield_textInputCursorStart(this) + content.length,
                __mfield_textInputCursorEnd: this.__mfield_textInputCursorStart(this) + content.length,
            });
        }

        insertSuggestion() {
            const cursorPosition = this.__mfield_textInputCursorStart(this);
            let textLeft = this.__mfield_textInputContent(this).substring(
                0,
                this.__mfield_textInputContent(this).substring(0, cursorPosition).lastIndexOf(this.__mfield_suggestionDelimiter(this)) + 1
            );
            let textRight = this.__mfield_textInputContent(this).substring(
                cursorPosition,
                this.__mfield_textInputContent(this).length
            );
            if (this.__mfield_suggestionDelimiter(this) === ':') {
                textLeft = this.__mfield_textInputContent(this).substring(
                    0,
                    this.__mfield_textInputContent(this).substring(0, cursorPosition).lastIndexOf(this.__mfield_suggestionDelimiter(this))
                );
                textRight = this.__mfield_textInputContent(this).substring(
                    cursorPosition,
                    this.__mfield_textInputContent(this).length
                );
            }
            let recordReplacement = "";
            switch (this.__mfield_activeSuggestedRecordName(this)) {
                case '__mfield_activeSuggestedCannedResponse':
                    recordReplacement = this[this.__mfield_activeSuggestedRecordName(this)](this).__mfield_substitution(this);
                    break;
                case '__mfield_activeSuggestedChannel':
                    recordReplacement = this[this.__mfield_activeSuggestedRecordName(this)](this).__mfield_name(this);
                    this.update({
                        __mfield_mentionedChannels: [['link', this[this.__mfield_activeSuggestedRecordName(this)](this)]],
                    });
                    break;
                case '__mfield_activeSuggestedChannelCommand':
                    recordReplacement = this[this.__mfield_activeSuggestedRecordName(this)](this).__mfield_name(this);
                    break;
                case '__mfield_activeSuggestedPartner':
                    recordReplacement = this[this.__mfield_activeSuggestedRecordName(this)](this).__mfield_name(this).replace(/ /g, '\u00a0');
                    this.update({
                        __mfield_mentionedPartners: [['link', this[this.__mfield_activeSuggestedRecordName(this)](this)]],
                    });
                    break;
            }
            this.update({
                __mfield_textInputContent: textLeft + recordReplacement + ' ' + textRight,
                __mfield_textInputCursorEnd: textLeft.length + recordReplacement.length + 1,
                __mfield_textInputCursorStart: textLeft.length + recordReplacement.length + 1,
            });
        }

        /**
         * @private
         * @returns {mail.partner[]}
         */
        _computeRecipients() {
            const recipients = [...this.__mfield_mentionedPartners(this)];
            if (this.__mfield_thread(this)) {
                for (const recipient of this.__mfield_thread(this).__mfield_suggestedRecipientInfoList(this)) {
                    if (recipient.__mfield_isSelected(this)) {
                        recipients.push(recipient.__mfield_partner(this));
                    }
                }
            }
            return [['replace', recipients]];
        }

        /**
         * Open the full composer modal.
         */
        async openFullComposer() {
            const attachmentIds = this.__mfield_attachments(this).map(attachment => attachment.__mfield_id(this));

            const context = {
                default_attachment_ids: attachmentIds,
                default_body: mailUtils.escapeAndCompactTextContent(this.__mfield_textInputContent(this)),
                default_is_log: this.__mfield_isLog(this),
                default_model: this.__mfield_thread(this).__mfield_model(this),
                default_partner_ids: this.__mfield_recipients(this).map(partner => partner.__mfield_id(this)),
                default_res_id: this.__mfield_thread(this).__mfield_id(this),
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
                    this.__mfield_thread(this).loadNewMessages();
                },
            };
            await this.env.bus.trigger('do-action', { action, options });
        }

        /**
         * Post a message in provided composer's thread based on current composer fields values.
         */
        async postMessage() {
            const thread = this.__mfield_thread(this);
            this.__mfield_thread(this).unregisterCurrentPartnerIsTyping({ immediateNotify: true });
            const escapedAndCompactContent = escapeAndCompactTextContent(this.__mfield_textInputContent(this));
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
                attachment_ids: this.__mfield_attachments(this).map(attachment => attachment.__mfield_id(this)),
                body,
                channel_ids: this.__mfield_mentionedChannels(this).map(channel => channel.__mfield_id(this)),
                context: {
                    mail_post_autofollow: true,
                },
                message_type: 'comment',
                partner_ids: this.__mfield_recipients(this).map(partner => partner.__mfield_id(this)),
            };
            if (this.__mfield_subjectContent(this)) {
                postData.subject = this.__mfield_subjectContent(this);
            }
            let messageId;
            if (thread.__mfield_model(this) === 'mail.channel') {
                const command = this._getCommandFromText(body);
                Object.assign(postData, {
                    command,
                    subtype_xmlid: 'mail.mt_comment'
                });
                messageId = await this.async(() => this.env.services.rpc({
                    model: 'mail.channel',
                    method: command ? 'execute_command' : 'message_post',
                    args: [thread.__mfield_id(this)],
                    kwargs: postData,
                }));
            } else {
                Object.assign(postData, {
                    subtype_xmlid: this.__mfield_isLog(this) ? 'mail.mt_note' : 'mail.mt_comment',
                });
                messageId = await this.async(() => this.env.services.rpc({
                    model: thread.__mfield_model(this),
                    method: 'message_post',
                    args: [thread.__mfield_id(this)],
                    kwargs: postData,
                }));
                const [messageData] = await this.async(() => this.env.services.rpc({
                    model: 'mail.message',
                    method: 'message_format',
                    args: [[messageId]],
                }));
                this.env.models['mail.message'].insert(Object.assign(
                    {},
                    this.env.models['mail.message'].convertData(messageData),
                    {
                        __mfield_originThread: [['insert', {
                            __mfield_id: thread.__mfield_id(this),
                            __mfield_model: thread.__mfield_model(this),
                        }]],
                    })
                );
                thread.loadNewMessages();
            }
            for (const threadView of this.__mfield_thread(this).__mfield_threadViews(this)) {
                threadView.addComponentHint('current-partner-just-posted-message', { messageId });
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
            if (!this.__mfield_thread(this)) {
                return;
            }
            if (this.__mfield_thread(this).__mfield_typingMembers(this).includes(this.env.messaging.__mfield_currentPartner(this))) {
                this.__mfield_thread(this).refreshCurrentPartnerIsTyping();
            } else {
                this.__mfield_thread(this).registerCurrentPartnerIsTyping();
            }
        }

        setFirstSuggestionActive() {
            if (!this[this.__mfield_mainSuggestedRecordsListName(this)](this)[0]) {
                if (!this[this.__mfield_extraSuggestedRecordsListName(this)](this)[0]) {
                    return;
                }
                this.update({
                    [this.__mfield_activeSuggestedRecordName(this)]: [['link', this[this.__mfield_extraSuggestedRecordsListName(this)](this)[0]]],
                });
            } else {
                this.update({
                    [this.__mfield_activeSuggestedRecordName(this)]: [['link', this[this.__mfield_mainSuggestedRecordsListName(this)](this)[0]]],
                });
            }
        }

        setLastSuggestionActive() {
            if (this[this.__mfield_extraSuggestedRecordsListName(this)](this).length === 0) {
                if (this[this.__mfield_mainSuggestedRecordsListName(this)](this).length === 0) {
                    return;
                }
                this.update({
                    [this.__mfield_activeSuggestedRecordName(this)]: [[
                        'link',
                        this[this.__mfield_mainSuggestedRecordsListName(this)](this)[this[this.__mfield_mainSuggestedRecordsListName(this)](this).length - 1]
                    ]],
                });
            }
            this.update({
                [this.__mfield_activeSuggestedRecordName(this)]: [[
                    'link',
                    this[this.__mfield_extraSuggestedRecordsListName(this)](this)[this[this.__mfield_extraSuggestedRecordsListName(this)](this).length - 1]
                ]],
            });
        }

        setNextSuggestionActive() {
            const fullList = this.__mfield_extraSuggestedRecordsListName(this) ?
                this[this.__mfield_mainSuggestedRecordsListName(this)].concat(this[this.__mfield_extraSuggestedRecordsListName(this)](this)) :
                this[this.__mfield_mainSuggestedRecordsListName(this)];
            if (fullList.length === 0) {
                return;
            }
            const activeElementIndex = fullList.findIndex(
                suggestion => suggestion === this[this.__mfield_activeSuggestedRecordName(this)](this)
            );
            if (activeElementIndex !== fullList.length - 1) {
                this.update({
                    [this.__mfield_activeSuggestedRecordName(this)]: [[
                        'link',
                        fullList[activeElementIndex + 1]
                    ]],
                });
            } else {
                this.update({
                    [this.__mfield_activeSuggestedRecordName(this)]: [['link', fullList[0]]],
                });
            }
        }

        setPreviousSuggestionActive() {
            const fullList = this.__mfield_extraSuggestedRecordsListName(this) ?
                this[this.__mfield_mainSuggestedRecordsListName(this)].concat(this[this.__mfield_extraSuggestedRecordsListName(this)](this)) :
                this[this.__mfield_mainSuggestedRecordsListName(this)];
            if (fullList.length === 0) {
                return;
            }
            const activeElementIndex = fullList.findIndex(
                suggestion => suggestion === this[this.__mfield_activeSuggestedRecordName(this)](this)
            );
            if (activeElementIndex === -1) {
                this.update({
                    [this.__mfield_activeSuggestedRecordName(this)]: [['link', fullList[0]]]
                });
            } else if (activeElementIndex !== 0) {
                this.update({
                    [this.__mfield_activeSuggestedRecordName(this)]: [[
                        'link',
                        fullList[activeElementIndex - 1]
                    ]],
                });
            } else {
                this.update({
                    [this.__mfield_activeSuggestedRecordName(this)]: [[
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
         * @returns {mail.model|undefined}
         */
        _computeActiveSuggestedRecord() {
            if (!this[this.__mfield_activeSuggestedRecordName(this)]) {
                return;
            }
            return this[this.__mfield_activeSuggestedRecordName(this)](this);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeCanPostMessage() {
            if (!this.__mfield_textInputContent(this) && this.__mfield_attachments(this).length === 0) {
                return false;
            }
            return !this.__mfield_hasUploadingAttachment(this);
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
            return [['unlink', this.__mfield_mainSuggestedPartners(this)]];
        }

        /**
         * @private
         * @returns {mail.model[]}
         */
        _computeExtraSuggestedRecordsList() {
            return this.__mfield_extraSuggestedRecordsListName(this)
                ? this[this.__mfield_extraSuggestedRecordsListName(this)](this)
                : [];
        }

        /**
         * @private
         * @return {boolean}
         */
        _computeHasSuggestions() {
            const hasMainSuggestedRecordsList = this.__mfield_mainSuggestedRecordsListName(this) ? this[this.__mfield_mainSuggestedRecordsListName(this)](this).length > 0 : false;
            const hasExtraSuggestedRecordsList = this.__mfield_extraSuggestedRecordsListName(this) ? this[this.__mfield_extraSuggestedRecordsListName(this)](this).length > 0 : false;
            return hasMainSuggestedRecordsList || hasExtraSuggestedRecordsList;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasUploadingAttachment() {
            return this.__mfield_attachments(this).some(attachment => attachment.__mfield_isTemporary(this));
        }

        /**
         * @private
         * @returns {mail.model[]}
         */
        _computeMainSuggestedRecordsList() {
            return this.__mfield_mainSuggestedRecordsListName(this)
                ? this[this.__mfield_mainSuggestedRecordsListName(this)](this)
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
            const inputMentions = this.__mfield_textInputContent(this).match(
                new RegExp("@[^ ]+(?= |&nbsp;|$)", 'g')
            ) || [];
            const unmentionedPartners = [];
            for (const partner of this.__mfield_mentionedPartners(this)) {
                let inputMention = inputMentions.find(item => {
                    return item === ("@" + partner.__mfield_name(this)).replace(/ /g, '\u00a0');
                });
                if (!inputMention) {
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
            const inputMentions = this.__mfield_textInputContent(this).match(
                new RegExp("#[^ ]+(?= |&nbsp;|$)", 'g')
            ) || [];
            const unmentionedChannels = [];
            for (const channel of this.__mfield_mentionedChannels(this)) {
                let inputMention = inputMentions.find(item => {
                    return item === ("#" + channel.__mfield_name(this)).replace(/ /g, '\u00a0');
                });
                if (!inputMention) {
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
            if (this.__mfield_mentionedPartners(this).length === 0 && this.__mfield_mentionedChannels(this).length === 0) {
                return body;
            }
            const inputMentions = body.match(new RegExp("(@|#)" + '[^ ]+(?= |&nbsp;|$)', 'g'));
            const substrings = [];
            let startIndex = 0;
            for (const match of inputMentions) {
                const suggestionDelimiter = match[0];
                const matchName = owl.utils.escape(match.substring(1).replace(new RegExp('\u00a0', 'g'), ' '));
                const endIndex = body.indexOf(match, startIndex) + match.length;
                let field = "__mfield_mentionedPartners";
                let model = "res.partner";
                let cssClass = "o_mail_redirect";
                if (suggestionDelimiter === "#") {
                    field = "__mfield_mentionedChannels";
                    model = "mail.channel";
                    cssClass = "o_channel_redirect";
                }
                const mention = this[field](this).find(mention =>
                    mention.__mfield_name(this) === matchName
                );
                let mentionLink = suggestionDelimiter + matchName;
                if (mention) {
                    const baseHREF = this.env.session.url('/web');
                    const href = `href='${baseHREF}#model=${model}&id=${mention.__mfield_id(this)}'`;
                    const attClass = `class='${cssClass}'`;
                    const dataOeId = `data-oe-id='${mention.__mfield_id(this)}'`;
                    const dataOeModel = `data-oe-model='${model}'`;
                    const target = `target='_blank'`;
                    mentionLink = `<a ${href} ${attClass} ${dataOeId} ${dataOeModel} ${target} >${suggestionDelimiter}${matchName}</a>`;
                }
                substrings.push(body.substring(startIndex, body.indexOf(match, startIndex)));
                substrings.push(mentionLink);
                startIndex = endIndex;
            }
            substrings.push(body.substring(startIndex, body.length));
            return substrings.join('');
        }

        /**
         * @private
         * @param {string} content html content
         * @returns {string|undefined} command, if any in the content
         */
        _getCommandFromText(content) {
            if (content.startsWith('/')) {
                return content.substring(1).split(/\s/)[0];
            }
            return undefined;
        }

        /**
         * @private
         */
        _reset() {
            this.closeSuggestions();
            this.update({
                __mfield_attachments: [['unlink-all']],
                __mfield_mentionedChannels: [['unlink-all']],
                __mfield_mentionedPartners: [['unlink-all']],
                __mfield_subjectContent: "",
                __mfield_textInputContent: '',
                __mfield_textInputCursorEnd: 0,
                __mfield_textInputCursorStart: 0,
            });
        }

        /**
         * @private
         * @param {string} mentionKeyword
         */
        _updateSuggestedCannedResponses(mentionKeyword) {
            this.update({
                __mfield_suggestedCannedResponses: [['replace', this.env.messaging.__mfield_cannedResponses(this).filter(
                    cannedResponse => (
                        cannedResponse.__mfield_source(this) &&
                        cannedResponse.__mfield_source(this).includes(mentionKeyword)
                    )
                )]],
            });

            if (this.__mfield_suggestedCannedResponses(this)[0]) {
                this.update({
                    __mfield_activeSuggestedCannedResponse: [['link', this.__mfield_suggestedCannedResponses(this)[0]]],
                });
            } else {
                this.update({
                    __mfield_activeSuggestedCannedResponse: [['unlink']],
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
                __mfield_suggestedChannels: [[
                    'insert-and-replace',
                    mentions.map(data =>
                        this.env.models['mail.thread'].convertData(data))
                    ]],
            });

            if (this.__mfield_suggestedChannels(this)[0]) {
                this.update({
                    __mfield_activeSuggestedChannel: [['link', this.__mfield_suggestedChannels(this)[0]]],
                });
            } else {
                this.update({
                    __mfield_activeSuggestedChannel: [['unlink']],
                });
            }
        }

        /**
         * @param {string} mentionKeyword
         */
        _updateSuggestedChannelCommands(mentionKeyword) {
            this.update({
                __mfield_suggestedChannelCommands: [[
                    'replace',
                    this.env.messaging.__mfield_commands(this).filter(
                        command => command.__mfield_name(this).includes(mentionKeyword)
                    )
                ]],
            });

            if (this.__mfield_suggestedChannelCommands(this)[0]) {
                this.update({
                    __mfield_activeSuggestedChannelCommand: [['link', this.__mfield_suggestedChannelCommands(this)[0]]],
                });
            } else {
                this.update({
                    __mfield_activeSuggestedChannelCommand: [['unlink']],
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
                __mfield_extraSuggestedPartners: [[
                    'insert-and-replace',
                    extraSuggestedPartners.map(data =>
                        this.env.models['mail.partner'].convertData(data)
                    )
                ]],
                __mfield_mainSuggestedPartners: [[
                    'insert-and-replace',
                    mainSuggestedPartners.map(data =>
                        this.env.models['mail.partner'].convertData(data))
                    ]],
            });

            if (this.__mfield_mainSuggestedPartners(this)[0]) {
                this.update({
                    __mfield_activeSuggestedPartner: [['link', this.__mfield_mainSuggestedPartners(this)[0]]],
                });
            } else if (this.__mfield_extraSuggestedPartners(this)[0]) {
                this.update({
                    __mfield_activeSuggestedPartner: [['link', this.__mfield_extraSuggestedPartners(this)[0]]],
                });
            } else {
                this.update({
                    __mfield_activeSuggestedPartner: [['unlink']],
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
            const leftString = this.__mfield_textInputContent(this).substring(0, this.__mfield_textInputCursorStart(this));

            // use position before suggestion delimiter because there should be whitespaces
            // or line feed/carriage return before the suggestion delimiter
            const beforeSuggestionDelimiterPosition = leftString.lastIndexOf(this.__mfield_suggestionDelimiter(this)) - 1;
            if (beginningOnly && beforeSuggestionDelimiterPosition > 0) {
                return false;
            }
            let searchStr = this.__mfield_textInputContent(this).substring(
                beforeSuggestionDelimiterPosition,
                this.__mfield_textInputCursorStart(this)
            );
            // regex string start with suggestion delimiter or whitespace then suggestion delimiter
            const pattern = "^" + this.__mfield_suggestionDelimiter(this) + "|^\\s" + this.__mfield_suggestionDelimiter(this);
            const regexStart = new RegExp(pattern, 'g');
            // trim any left whitespaces or the left line feed/ carriage return
            // at the beginning of the string
            searchStr = searchStr.replace(/^\s\s*|^[\n\r]/g, '');
            if (regexStart.test(searchStr) && searchStr.length) {
                searchStr = searchStr.replace(pattern, '');
                return !searchStr.includes(' ') && !/[\r\n]/.test(searchStr)
                    ? searchStr.replace(this.__mfield_suggestionDelimiter(this), '')
                    : false;
            }
            return false;
        }
    }

    Composer.fields = {
        __mfield_activeSuggestedCannedResponse: many2one('mail.canned_response'),
        __mfield_activeSuggestedChannel: many2one('mail.thread'),
        __mfield_activeSuggestedChannelCommand: many2one('mail.channel_command'),
        __mfield_activeSuggestedPartner: many2one('mail.partner'),
        __mfield_activeSuggestedRecord: attr({
            compute: '_computeActiveSuggestedRecord',
            dependencies: [
                '__mfield_activeSuggestedCannedResponse',
                '__mfield_activeSuggestedChannel',
                '__mfield_activeSuggestedChannelCommand',
                '__mfield_activeSuggestedPartner',
                '__mfield_activeSuggestedRecordName',
            ],
        }),
        __mfield_activeSuggestedRecordName: attr(),
        __mfield_attachments: many2many('mail.attachment', {
            inverse: '__mfield_composers',
        }),
        /**
         * This field watches the uploading (= temporary) status of attachments
         * linked to this composer.
         *
         * Useful to determine whether there are some attachments that are being
         * uploaded.
         */
        __mfield_attachmentsAreTemporary: attr({
            related: '__mfield_attachments.__mfield_isTemporary',
        }),
        __mfield_canPostMessage: attr({
            compute: '_computeCanPostMessage',
            dependencies: [
                '__mfield_attachments',
                '__mfield_hasUploadingAttachment',
                '__mfield_textInputContent',
            ],
            default: false,
        }),
        /**
         * Instance of discuss if this composer is used as the reply composer
         * from Inbox. This field is computed from the inverse relation and
         * should be considered read-only.
         */
        __mfield_discussAsReplying: one2one('mail.discuss', {
            inverse: '__mfield_replyingToMessageOriginThreadComposer',
        }),
        __mfield_extraSuggestedPartners: many2many('mail.partner', {
            compute: '_computeExtraSuggestedPartners',
            dependencies: [
                '__mfield_extraSuggestedPartners',
                '__mfield_mainSuggestedPartners',
            ],
        }),
        __mfield_extraSuggestedRecordsList: attr({
            compute: '_computeExtraSuggestedRecordsList',
            dependencies: [
                '__mfield_extraSuggestedPartners',
                '__mfield_extraSuggestedRecordsListName',
            ],
        }),
        /**
         * Allows to have different model types of mentions through a dynamic process
         * RPC can provide 2 lists and the second is defined as "extra"
         */
        __mfield_extraSuggestedRecordsListName: attr({
           default: "",
        }),
        /**
         * This field determines whether some attachments linked to this
         * composer are being uploaded.
         */
        __mfield_hasUploadingAttachment: attr({
            compute: '_computeHasUploadingAttachment',
            dependencies: [
                '__mfield_attachments',
                '__mfield_attachmentsAreTemporary',
            ],
        }),
        __mfield_hasFocus: attr({
            default: false,
        }),
        __mfield_hasSuggestions: attr({
            compute: '_computeHasSuggestions',
            dependencies: [
                '__mfield_extraSuggestedRecordsListName',
                '__mfield_extraSuggestedPartners',
                '__mfield_mainSuggestedRecordsListName',
                '__mfield_mainSuggestedPartners',
                '__mfield_suggestedCannedResponses',
                '__mfield_suggestedChannelCommands',
                '__mfield_suggestedChannels',
            ],
            default: false,
        }),
        /**
         * If true composer will log a note, else a comment will be posted.
         */
        __mfield_isLog: attr({
            default: false,
        }),
        __mfield_mainSuggestedRecordsList: attr({
            compute: '_computeMainSuggestedRecordsList',
            dependencies: [
                '__mfield_mainSuggestedPartners',
                '__mfield_mainSuggestedRecordsListName',
                '__mfield_suggestedCannedResponses',
                '__mfield_suggestedChannelCommands',
                '__mfield_suggestedChannels',
            ],
        }),
        /**
         * Allows to have different model types of mentions through a dynamic process
         * RPC can provide 2 lists and the first is defined as "main"
         */
        __mfield_mainSuggestedRecordsListName: attr({
           default: "",
        }),
        __mfield_mainSuggestedPartners: many2many('mail.partner'),
        __mfield_mentionedChannels: many2many('mail.thread', {
            compute: '_computeMentionedChannels',
            dependencies: ['__mfield_textInputContent'],
        }),
        __mfield_mentionedPartners: many2many('mail.partner', {
            compute: '_computeMentionedPartners',
            dependencies: [
                '__mfield_textInputContent',
            ],
        }),
        /**
         * Determines the extra `mail.partner` (on top of existing followers)
         * that will receive the message being composed by `this`, and that will
         * also be added as follower of `this.thread`.
         */
        __mfield_recipients: many2many('mail.partner', {
            compute: '_computeRecipients',
            dependencies: [
                '__mfield_mentionedPartners',
                '__mfield_threadSuggestedRecipientInfoListIsSelected',
                // FIXME thread.suggestedRecipientInfoList.partner should be a
                // dependency, but it is currently impossible to have a related
                // m2o through a m2m. task-2261221
            ]
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_threadSuggestedRecipientInfoList: many2many('mail.suggested_recipient_info', {
            related: '__mfield_thread.__mfield_suggestedRecipientInfoList',
        }),
        /**
         * Serves as compute dependency.
         */
        __mfield_threadSuggestedRecipientInfoListIsSelected: attr({
            related: '__mfield_threadSuggestedRecipientInfoList.__mfield_isSelected',
        }),
        /**
         * Composer subject input content.
         */
        __mfield_subjectContent: attr({
            default: "",
        }),
        __mfield_suggestedCannedResponses: many2many('mail.canned_response'),
        __mfield_suggestedChannelCommands: many2many('mail.channel_command'),
        __mfield_suggestedChannels: many2many('mail.thread'),
        /**
         * Special character used to trigger different kinds of suggestions
         * such as canned responses (:), channels (#), commands (/) and partners (@)
         */
        __mfield_suggestionDelimiter: attr({
            default: "",
        }),
        __mfield_suggestionModelName: attr({
           default: "",
        }),
        __mfield_textInputContent: attr({
            default: "",
        }),
        __mfield_textInputCursorEnd: attr({
            default: 0,
        }),
        __mfield_textInputCursorStart: attr({
            default: 0,
        }),
        __mfield_thread: one2one('mail.thread', {
            inverse: '__mfield_composer',
        }),
    };

    Composer.modelName = 'mail.composer';

    return Composer;
}

registerNewModel('mail.composer', factory);

});
