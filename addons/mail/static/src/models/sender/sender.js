odoo.define('mail/static/src/models/sender/sender.js', function (require) {
'use strict';

const emojis = require('mail.emojis');
const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, one2many, one2one } = require('mail/static/src/model/model_field.js');

const {
    addLink,
    escapeAndCompactTextContent,
    parseAndTransform,
} = require('mail.utils');

function factory(dependencies) {

    class Sender extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Queue a message and start to process it.
         */
        insertMessageToBeSent() {
            const composer = this.thread.composer;
            this.update({
                pendingMessagesToBeSent: [['insert', {
                    attachments: [['link', composer.attachments]],
                    author: [['link', this.env.messaging.currentPartner]],
                    body: this._convertMessageToHtml(),
                    channel_ids: composer.mentionedChannels.map(channel => channel.id),
                    composer: [['link', composer]],
                    date: moment(),
                    id: this.env.models['mail.message'].getNextTemporaryId(),
                    isPendingSend: true,
                    isTemporary: true,
                    isTransient: true,
                    is_discussion: true,
                    message_type: 'comment',
                    originThread: [['insert', {
                        id: composer.thread.id,
                        model: composer.thread.model,
                    }]],
                    partner_ids: composer.recipients.map(partner => partner.id),
                    subject: (composer.subjectContent) ? composer.subjectContent : undefined,
                }]]
            });
            composer._reset();
            for (const threadView of composer.thread.threadViews) {
                threadView.addComponentHint('new-message-posted');
            }
            this._processMessagesToBeSent();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Convert text message to HTML.
         *
         * @private
         * @returns {String}
         */
        _convertMessageToHtml() {
            const escapedAndCompactContent = escapeAndCompactTextContent(this.thread.composer.textInputContent);
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
            return body;
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
            for (const partner of this.thread.composer.mentionedPartners) {
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
            for (const channel of this.thread.composer.mentionedChannels) {
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
         * Function that process the message stored to be sent.
         */
        async _processMessagesToBeSent() {
            if (!this.isProcessingMessagesToBeSent) {
                this.update({
                    isSendingMessages: true,
                });
                const messages = this.pendingMessagesToBeSent.filter((message) => !message.hasSendError);
                const message = messages[0];
                try {
                    if (message) {
                        const thread = this.thread;
                        let postData = {
                            attachment_ids: message.attachments.map(attachement => attachement.id),
                            body: message.body,
                            channel_ids: message.channel_ids,
                            message_type: 'comment',
                            partner_ids: message.partner_ids,
                            subject: message.subject,
                        };
                        let messageId;
                        if (thread.model === 'mail.channel') {
                            const command = this.thread.composer._getCommandFromText(postData.body);
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
                                subtype_xmlid: this.thread.composer.isLog ? 'mail.mt_note' : 'mail.mt_comment',
                            });
                            if (!this.thread.composer.isLog) {
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
                        message.delete();
                    }
                    if (!messages.length) {
                        this.thread.refreshFollowers();
                        this.thread.fetchAndUpdateSuggestedRecipients();
                    }
                } catch (error) {
                    message.update({ hasSendError: true });
                } finally {
                    this.update({
                        isSendingMessages: false,
                    });
                    if (messages.length > 0) {
                        this._processMessagesToBeSent();
                    }
                }
            }
        }
    }

    Sender.fields = {
        thread: one2one('mail.thread', {
            inverse: 'sender'
        }),
        /**
         * Determine the messages pending to be sent to the server by
         * `processMessageToBeSent`. They will be sent one by one in queue order
         * (lastest to newest).
         */
        pendingMessagesToBeSent: one2many('mail.message'),
        /**
         * Determines whether messages are being sent to the server
         */
        isSendingMessages: attr({
            default: false
        }),
    };

    Sender.modelName = 'mail.sender';

    return Sender;
}

registerNewModel('mail.sender', factory);

});
