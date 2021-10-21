/** @odoo-module **/

import { emojis } from '@mail/js/emojis';
import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one, one2many } from '@mail/model/model_field';
import { addLink, escapeAndCompactTextContent, parseAndTransform } from '@mail/js/utils';
import { clear, link } from '@mail/model/model_field_command';

function factory(dependencies) {

    class ComposerMessageSender extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Queue a message to be sent and start the queue process.
         *
         * @param {mail.message}
         */
        sendMessage(message) {
            // Command are not really sent to the server like other messages.
            // They do not need the message queue to work and can be processed
            // early.
            const composer = this.composerView.composer;
            if (composer.thread.model === 'mail.channel') {
                const command = this._getCommandFromText(message.body);
                if (command) {
                    command.execute({ channel: composer.thread, body: message.body });
                    if (composer.exists()) {
                        composer._reset();
                    }
                    return;
                }
            }

            this.update({ messagesPendingToBeSent: link(message) });
            this._processMessageToBeSent();
        }

        convertMessageToHtml(text) {
            if (!text) {
                return;
            }
            const escapedAndCompactContent = escapeAndCompactTextContent(text);
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

        async _processMessageToBeSent() {
            // We are already sending message when `this.isSendingMessages` is true.
            // This will prevent multiple queue to run at once.
            if (this.isSendingMessages) {
                return;
            }

            // Lock the message queue
            this.update({ isSendingMessages: true });

            const composer = this.composerView.composer;
            if (this.messaging.currentPartner) {
                composer.thread.unregisterCurrentPartnerIsTyping({ immediateNotify: true });
            }
            const messagePending = this.messagesPendingToBeSent[0];
            const postData = {
                attachment_ids: messagePending.attachment_ids,
                body: messagePending.body,
                message_type: 'comment',
                partner_ids: composer.recipients.map(partner => partner.id),
            };
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
                if (this.composerView.threadView && this.composerView.threadView.replyingToMessageView && this.composerView.threadView.thread !== this.messaging.inbox) {
                    postData.parent_id = this.composerView.threadView.replyingToMessageView.message.id;
                }
                const { threadView = {} } = this.composerView;
                const { thread: chatterThread } = this.composerView.chatter || {};
                const { thread: threadViewThread } = threadView;

                this.env.services.rpc({
                    route: `/mail/message/post`,
                    params
                }, { shadow: true })
                    .then((messageData) => {
                        const message = this.messaging.models['mail.message'].insert(
                            this.messaging.models['mail.message'].convertData(messageData)
                        );
                        for (const threadView of message.originThread.threadViews) {
                            // Reset auto scroll to be able to see the newly posted message.
                            threadView.update({ hasAutoScrollOnMessageReceived: true });
                        }
                        if (!this.messaging) {
                            return;
                        }
                        // We cannot simply update the temporary message with the
                        // real data since we don't have a we to link temporary
                        // message and the message comming from the bus. We delete
                        // the temporary message after sending it to the server and
                        // let the bus handle the update
                        messagePending.delete();
                        if (chatterThread) {
                            if (this.composerView.exists()) {
                                this.composerView.delete();
                            }
                            if (chatterThread.exists()) {
                                chatterThread.refreshFollowers();
                                chatterThread.fetchAndUpdateSuggestedRecipients();
                            }
                        }
                        if (threadViewThread) {
                            if (threadViewThread === this.messaging.inbox) {
                                if (this.composerView.exists()) {
                                    this.composerView.delete();
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

                        this.update({ isSendingMessages: false });
                        if (this.messagesPendingToBeSent.length > 0) {
                            this._processMessagesToBeSent();
                        }
                        if (composer.exists()) {
                            composer._reset();
                        }
                    }, () =>  {
                        this.update({ isSendingMessages: false });
                        this.composerView.composer.update({
                            textInputContent: messagePending.rawBody,
                        });
                    });
            }
            finally {
                if (composer.exists()) {
                    composer.update({ isPostingMessage: false });
                }
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

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
            for (const partner of this.composerView.composer.mentionedPartners) {
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
            for (const channel of this.composerView.composer.mentionedChannels) {
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
        }
    }

    ComposerMessageSender.fields = {
        /**
         * Determines whether messages are being sent to the server
         */
        isSendingMessages: attr({
            default: false,
        }),
        /**
         * Determine the messages pending to be sent to the server by
         * `processMessageToBeSent`. They will be sent one by one in queue order
         * (first in, first out).
         */
        messagesPendingToBeSent: one2many('mail.message', {
            default: [],
        }),
        /**
         * States the composerView linked to this sender.
         */
        composerView: one2one('mail.composer_view', {
            inverse: 'messageSender',
            readonly: true,
        })
    };

    ComposerMessageSender.identifyingFields = ['composerView'];
    ComposerMessageSender.modelName = 'mail.composer_message_sender';

    return ComposerMessageSender;
}

registerNewModel('mail.composer_message_sender', factory);
