/** @odoo-module **/

import emojis from '@mail/js/emojis';
import { registerNewModel } from '@mail/model/model_core';
import { attr, one2many, one2one } from '@mail/model/model_field';
import { link, unlink } from '@mail/model/model_field_command';

import {
    addLink,
    escapeAndCompactTextContent,
    parseAndTransform,
 } from '@mail/js/utils';

function factory(dependencies) {

    class ThreadMessageSender extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Convert text message to HTML.
         *
         * @private
         * @param {string} text
         * @returns {String}
         */
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

        /**
         * Queue a message and start to process it.
         *
         * @param {mail.message} message
         */
        sendMessage(message) {
            this.update({
                messagesPendingToBeSent: link(message),
                messagesThatFailedToBeSent: unlink(message),
            });
            this._processMessagesToBeSent();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Generates the html link related to the mentioned channels and
         * partners
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
         * Send a message to the server based on the thread model and handle RPC
         * error.
         * @private
         * @param {Object} options
         */
        async _processMessagesToBeSent() {
            if (this.isSendingMessages) {
                return;
            }
            this.update({ isSendingMessages: true });
            const messagePending = this.messagesPendingToBeSent[0];
            try {
                const postData = {
                    attachment_ids: messagePending.attachments.map(attachement => attachement.id),
                    body: messagePending.body,
                    message_type: 'comment',
                    partner_ids: this.thread.composer.recipients.map(partner => partner.id),
                };
                const params = {
                    'post_data': postData,
                    'thread_id': this.thread.id,
                    'thread_model': this.thread.model,
                };
                if (this.thread.model === 'mail.channel') {
                    Object.assign(postData, {
                        subtype_xmlid: 'mail.mt_comment',
                    });
                } else {
                    Object.assign(postData, {
                        subtype_xmlid: this.thread.composer.isLog ? 'mail.mt_note' : 'mail.mt_comment',
                    });
                    if (!this.isLog) {
                        params.context = { mail_post_autofollow: true };
                    }
                }
                const messageData = await this.env.services.rpc({
                    route: `/mail/message/post`,
                    params,
                }, {
                    shadow: true,
                });
                if (!this.messaging) {
                    return;
                }
                const message = this.messaging.models['mail.message'].insert(
                    this.messaging.models['mail.message'].convertData(messageData)
                );
                for (const threadView of message.originThread.threadViews) {
                    // Reset auto scroll to be able to see the newly posted message.
                    threadView.update({ hasAutoScrollOnMessageReceived: true });
                }
                if (messagePending.afterSendCallback) {
                    messagePending.afterSendCallback();
                }
                // We cannot simply update the temporary message with the
                // real data since we don't have a we to link temporary
                // message and the message comming from the bus. We delete
                // the temporary message after sending it to the server and
                // let the bus handle the update
                messagePending.delete();
                if (this.messagesPendingToBeSent.length > 0 && this.thread.model !== 'mail.channel') {
                    this.thread.refreshFollowers();
                    this.thread.fetchAndUpdateSuggestedRecipients();
                }
                this.update({ isSendingMessages: false });
                if (this.messagesPendingToBeSent.length > 0) {
                    this._processMessagesToBeSent();
                }
            } catch (error) {
                this.update({
                    isSendingMessages: false,
                    messagesPendingToBeSent: unlink(messagePending),
                    messagesThatFailedToBeSent: link(messagePending),
                });
            }
        }

    }

    ThreadMessageSender.fields = {
        /**
         * Determines whether messages are being sent to the server
         */
        isSendingMessages: attr({
            default: false
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
         * Determine the messages that could not be sent to the server due to an
         * error.
         */
        messagesThatFailedToBeSent: one2many('mail.message', {
            default: [],
        }),
        /**
         * Origin thread of the message.
         */
        thread: one2one('mail.thread', {
            inverse: 'messageSender',
            required: true,
            readonly: true,
        }),
    };
    ThreadMessageSender.identifyingFields = ['thread'];

    ThreadMessageSender.modelName = 'mail.thread_message_sender';

    return ThreadMessageSender;
}

registerNewModel('mail.thread_message_sender', factory);
