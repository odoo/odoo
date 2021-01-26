odoo.define('mail/static/src/models/composer/composer.js', function (require) {
'use strict';

const emojis = require('mail.emojis');
const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, one2one } = require('mail/static/src/model/model_field.js');
const { create, insert, link, replace, unlink, unlinkAll } = require('mail/static/src/model/model_field_command.js');
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
            let suggestionDelimiterPosition = this.suggestionManager.suggestionDelimiterPosition;
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
                this.suggestionManager.suggestionDelimiterPosition + 1
            );
            let textRight = this.textInputContent.substring(
                cursorPosition,
                this.textInputContent.length
            );
            if (this.suggestionManager.suggestionDelimiter === ':') {
                textLeft = this.textInputContent.substring(
                    0,
                    this.suggestionManager.suggestionDelimiterPosition
                );
                textRight = this.textInputContent.substring(
                    cursorPosition,
                    this.textInputContent.length
                );
            }
            const recordReplacement = this.suggestionManager.activeSuggestedRecord.getMentionText();
            const updateData = {
                isLastStateChangeProgrammatic: true,
                textInputContent: textLeft + recordReplacement + ' ' + textRight,
                textInputCursorEnd: textLeft.length + recordReplacement.length + 1,
                textInputCursorStart: textLeft.length + recordReplacement.length + 1,
            };
            // Specific cases for channel and partner mentions: the message with
            // the mention will appear in the target channel, or be notified to
            // the target partner.
            switch (this.suggestionManager.activeSuggestedRecord.constructor.modelName) {
                case 'mail.thread':
                    Object.assign(updateData, { mentionedChannels: link(this.suggestionManager.activeSuggestedRecord) });
                    break;
                case 'mail.partner':
                    Object.assign(updateData, { mentionedPartners: link(this.suggestionManager.activeSuggestedRecord) });
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
                this.suggestionManager.suggestionModelName === 'mail.channel_command' ||
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

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

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

        _computeSuggestionManager() {
            if (this.suggestionManager) {
                return;
            }
            return create({ thread: link(this.thread) });
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
            this.suggestionManager.closeSuggestions();
            this.suggestionManager.update({
                textInputContent: '',
                textInputCursorEnd: 0,
                textInputCursorStart: 0,
            });
            this.update({
                attachments: unlinkAll(),
                isLastStateChangeProgrammatic: true,
                mentionedChannels: unlinkAll(),
                mentionedPartners: unlinkAll(),
                subjectContent: "",
                textInputContent: '',
                textInputCursorEnd: 0,
                textInputCursorStart: 0,
            });
        }

    }

    Composer.fields = {
        attachments: many2many('mail.attachment', {
            inverse: 'composers',
        }),
        /**
         * This field watches the uploading status of attachments linked to this composer.
         *
         * Useful to determine whether there are some attachments that are being
         * uploaded.
         */
        attachmentsAreUploading: attr({
            related: 'attachments.isUploading',
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
         * This field determines whether some attachments linked to this
         * composer are being uploaded.
         */
        hasUploadingAttachment: attr({
            compute: '_computeHasUploadingAttachment',
            dependencies: [
                'attachments',
                'attachmentsAreUploading',
            ],
        }),
        hasFocus: attr({
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
        suggestionManager: one2one('mail.suggestionManager', {
            compute: '_computeSuggestionManager',
            dependencies: [
                'thread'
            ]
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
            required: true,
        }),
    };

    Composer.modelName = 'mail.composer';

    return Composer;
}

registerNewModel('mail.composer', factory);

});
