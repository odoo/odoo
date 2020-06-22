odoo.define('mail/static/src/models/composer/composer.js', function (require) {
'use strict';

const emojis = require('mail.emojis');
const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2one } = require('mail/static/src/model/model_field.js');

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

        closeMentionSuggestions() {
            this.update({
                activeSuggestedPartner: [['unlink']],
                extraSuggestedPartners: [['unlink-all']],
                mainSuggestedPartners: [['unlink-all']],
            });
        }

        discard() {
            const discuss = this.env.messaging.discuss;
            const thread = this.thread;
            if (
                !discuss.isOpen ||
                discuss.thread !== thread ||
                !discuss.isReplyingToMessage
            ) {
                return;
            }
            discuss.clearReplyingToMessage();
        }

        focus() {
            this.update({ isDoFocus: true });
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

        /**
         * @param {mail.partner} partner
         */
        insertMentionedPartner(partner) {
            const cursorPosition = this.textInputCursorStart;
            const textLeft = this.textInputContent.substring(
                0,
                this.textInputContent.substring(0, cursorPosition).lastIndexOf('@') + 1
            );
            const textRight = this.textInputContent.substring(
                cursorPosition,
                this.textInputContent.length
            );
            const partnerName = partner.name.replace(/ /g, '\u00a0');
            this.update({
                mentionedPartners: [['link', partner]],
                textInputContent: textLeft + partnerName + ' ' + textRight,
                textInputCursorEnd: textLeft.length + partnerName.length + 1,
                textInputCursorStart: textLeft.length + partnerName.length + 1,
            });
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
                partner_ids: this.mentionedPartners.map(partner => partner.id),
                message_type: 'comment',
            };
            let messageId;
            if (thread.model === 'mail.channel') {
                const command = this._getCommandFromText(body);
                Object.assign(postData, {
                    command,
                    subtype_xmlid: 'mail.mt_comment'
                });
                messageId = await this.async(() => this.env.services.rpc({
                    model: 'mail.channel',
                    method: command ? 'execute_command' : 'message_post',
                    args: [thread.id],
                    kwargs: postData
                }));
            } else {
                Object.assign(postData, {
                    subtype_xmlid: this.isLog ? 'mail.mt_note' : 'mail.mt_comment',
                });
                messageId = await this.async(() => this.env.services.rpc({
                    model: thread.model,
                    method: 'message_post',
                    args: [thread.id],
                    kwargs: postData
                }));
                const [messageData] = await this.async(() => this.env.services.rpc({
                    model: 'mail.message',
                    method: 'message_format',
                    args: [[messageId]]
                }));
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
            for (const threadViewer of this.thread.viewers) {
                threadViewer.addComponentHint('current-partner-just-posted-message', messageId);
            }
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

        setFirstSuggestedPartnerActive() {
            if (!this.allSuggestedPartners[0]) {
                return;
            }
            this.update({
                activeSuggestedPartner: [['link', this.allSuggestedPartners[0]]],
            });
        }

        setLastSuggestedPartnerActive() {
            if (this.allSuggestedPartners.length === 0) {
                return;
            }
            this.update({
                activeSuggestedPartner: [[
                    'link',
                    this.allSuggestedPartners[this.allSuggestedPartners.length - 1]
                ]],
            });
        }

        setNextSuggestedPartnerActive() {
            if (this.allSuggestedPartners.length === 0) {
                return;
            }
            const activeSuggestedPartnerIndex = this.allSuggestedPartners.findIndex(
                suggestedPartner => suggestedPartner === this.activeSuggestedPartner
            );
            if (activeSuggestedPartnerIndex !== this.allSuggestedPartners.length - 1) {
                this.update({
                    activeSuggestedPartner: [[
                        'link',
                        this.allSuggestedPartners[activeSuggestedPartnerIndex + 1]
                    ]],
                });
            } else {
                this.update({
                    activeSuggestedPartner: [['link', this.allSuggestedPartners[0]]],
                });
            }
        }

        setPreviousSuggestedPartnerActive() {
            if (this.allSuggestedPartners.length === 0) {
                return;
            }
            const activeSuggestedPartnerIndex = this.allSuggestedPartners.findIndex(
                suggestedPartner => suggestedPartner === this.activeSuggestedPartner
            );
            if (activeSuggestedPartnerIndex === -1) {
                this.update({
                    activeSuggestedPartner: [['link', this.allSuggestedPartners[0]]]
                });
            } else if (activeSuggestedPartnerIndex !== 0) {
                this.update({
                    activeSuggestedPartner: [[
                        'link',
                        this.allSuggestedPartners[activeSuggestedPartnerIndex - 1]
                    ]],
                });
            } else {
                this.update({
                    activeSuggestedPartner: [[
                        'link',
                        this.allSuggestedPartners[this.allSuggestedPartners.length - 1]
                    ]],
                });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.partner[]}
         */
        _computeAllSuggestedPartners() {
            return [['replace', this.mainSuggestedPartners.concat(this.extraSuggestedPartners)]];
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeCanPostMessage() {
            return this.textInputContent || this.attachments.length !== 0;
        }

        /**
         * Ensure extraSuggestedPartners does not contain any partner already
         * present in mainSuggestedPartners. This is necessary for the
         * consistency of suggestion list because allSuggestedPartners is the
         * union of both but without duplicates (because it is a relational
         * field).
         *
         * @private
         * @returns {mail.partner[]}
         */
        _computeExtraSuggestedPartners() {
            return [['unlink', this.mainSuggestedPartners]];
        }

        /**
         * @private
         * @return {boolean}
         */
        _computeHasSuggestedPartners() {
            return this.allSuggestedPartners.length > 0;
        }

        /**
         * Detects if mentioned partners are still in the composer text input content
         * and removes them if not.
         *
         * @private
         * @returns {mail.partner[]}
         */
        _computeMentionedPartners() {
            const inputMentions = this.textInputContent.match(
                new RegExp("@[^ ]+(?= |&nbsp;|$)", 'g')
            ) || [];
            const unmentionedPartners = [];
            for (const partner of this.mentionedPartners) {
                let inputMention = inputMentions.find(item => {
                    return item === ("@" + partner.name).replace(/ /g, '\u00a0');
                });
                if (!inputMention) {
                    unmentionedPartners.push(partner);
                }
            }
            return [['unlink', unmentionedPartners]];
        }

        /**
         * Detects if mentions suggestions should be displayed when user is typing
         * and searches partners based on user's research.
         *
         * @private
         */
        _detectDelimiter() {
            const mentionKeyword = this._validateMentionKeyword('@', false);
            if (mentionKeyword !== false) {
                this._getSuggestedPartners(mentionKeyword);
            } else {
                this.closeMentionSuggestions();
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
            if (this.mentionedPartners.length === 0) {
                return body;
            }
            const inputMentions = body.match(new RegExp("@"+'[^ ]+(?= |&nbsp;|$)', 'g'));
            const substrings = [];
            let startIndex = 0;
            for (const i in inputMentions) {
                const match = inputMentions[i];
                const matchName = owl.utils.escape(match.substring(1).replace(new RegExp('\u00a0', 'g'), ' '));
                const endIndex = body.indexOf(match, startIndex) + match.length;
                const partner = this.mentionedPartners.find(partner =>
                    partner.name === matchName
                );
                let mentionLink = "@" + matchName;
                if (partner) {
                    const baseHREF = this.env.session.url('/web');
                    const href = `href='${baseHREF}#model=res.partner&id=${partner.id}'`;
                    const attClass = `class='o_mail_redirect'`;
                    const dataOeId = `data-oe-id='${partner.id}'`;
                    const dataOeModel = `data-oe-model='res.partner'`;
                    const target = `target='_blank'`;
                    mentionLink = `<a ${href} ${attClass} ${dataOeId} ${dataOeModel} ${target} >@${matchName}</a>`;
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
         * @param {string} mentionKeyword
         */
        async _getSuggestedPartners(mentionKeyword) {
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

            if (this.allSuggestedPartners[0]) {
                this.update({
                    activeSuggestedPartner: [['link', this.allSuggestedPartners[0]]],
                });
            } else {
                this.update({
                    activeSuggestedPartner: [['unlink']],
                });
            }
        }

        /**
         * @private
         */
        _reset() {
            this.closeMentionSuggestions();
            this.update({
                attachments: [['unlink-all']],
                mentionedPartners: [['unlink-all']],
                textInputContent: '',
                textInputCursorStart: 0,
                textInputCursorEnd: 0,
            });
        }

        /**
         * Validates user's current typing as a correct mention keyword
         * in order to trigger mentions suggestions display.
         * Returns the mention keyword without the delimiter if it has been validated
         * and false if not
         *
         * @private
         * @param {string} delimiter
         * @param {boolean} beginningOnly
         * @returns {string|boolean}
         */
        _validateMentionKeyword(delimiter, beginningOnly) {
            const leftString = this.textInputContent.substring(0, this.textInputCursorStart);

            // use position before delimiter because there should be whitespaces
            // or line feed/carriage return before the delimiter
            const beforeDelimiterPosition = leftString.lastIndexOf(delimiter) - 1;
            if (beginningOnly && beforeDelimiterPosition > 0) {
                return false;
            }
            let searchStr = this.textInputContent.substring(
                beforeDelimiterPosition,
                this.textInputCursorStart
            );
            // regex string start with delimiter or whitespace then delimiter
            const pattern = "^"+delimiter+"|^\\s"+delimiter;
            const regexStart = new RegExp(pattern, 'g');
            // trim any left whitespaces or the left line feed/ carriage return
            // at the beginning of the string
            searchStr = searchStr.replace(/^\s\s*|^[\n\r]/g, '');
            if (regexStart.test(searchStr) && searchStr.length) {
                searchStr = searchStr.replace(pattern, '');
                return !searchStr.includes(' ') && !/[\r\n]/.test(searchStr)
                    ? searchStr.replace(delimiter, '')
                    : false;
            }
            return false;
        }
    }

    Composer.fields = {
        activeSuggestedPartner: many2one('mail.partner'),
        allSuggestedPartners: many2many('mail.partner', {
            compute: '_computeAllSuggestedPartners',
            dependencies: [
                'extraSuggestedPartners',
                'mainSuggestedPartners',
            ],
        }),
        attachments: many2many('mail.attachment', {
            inverse: 'composers',
        }),
        canPostMessage: attr({
            compute: '_computeCanPostMessage',
            dependencies: [
                'attachments',
                'textInputContent',
            ],
            default: false,
        }),
        extraSuggestedPartners: many2many('mail.partner', {
            compute: '_computeExtraSuggestedPartners',
            dependencies: [
                'extraSuggestedPartners',
                'mainSuggestedPartners',
            ],
        }),
        hasFocus: attr({
            default: false,
        }),
        hasSuggestedPartners: attr({
            compute: '_computeHasSuggestedPartners',
            dependencies: [
                'allSuggestedPartners',
            ],
            default: false,
        }),
        isDoFocus: attr({
            default: false,
        }),
        /**
         * If true composer will log a note, else a comment will be posted.
         */
        isLog: attr({
            default: false,
        }),
        mainSuggestedPartners: many2many('mail.partner'),
        mentionedPartners: many2many('mail.partner', {
            compute: '_computeMentionedPartners',
            dependencies: ['textInputContent'],
        }),
        textInputContent: attr({
            default: "",
        }),
        textInputCursorStart: attr({
            default: 0,
        }),
        textInputCursorEnd: attr({
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
