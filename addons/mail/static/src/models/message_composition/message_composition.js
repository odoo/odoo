/** @odoo-module **/

import { emojis } from '@mail/js/emojis';
import { registerNewModel } from '@mail/model/model_core';
import { unlink, replace } from '@mail/model/model_field_command';
import { attr, many2many, one2one } from '@mail/model/model_field';
import { addLink, escapeAndCompactTextContent, parseAndTransform } from '@mail/js/utils';

function factory(dependencies) {

    class MessageComposition extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * This method will generate the html body of a message, create the
         * link, mention link, channel link, and convert the emoji's.
         * This is intentionnaly NOT a compute to avoid possible performance issue.
         *
         * @return void
         */
        generateBody() {
            const escapedAndCompactContent = escapeAndCompactTextContent(this.rawBody);
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
            this.update({ body });
        }

        /**
         * Remove suggestions from the message composition.
         *
         * @return void
         */
        removeSuggestions() {
            // ensure the same mention is not used multiple times if multiple
            // partners have the same name
            const mentionIndex = {};
            for (const partner of this.mentionedPartners) {
                const fromIndex = mentionIndex[partner.name] !== undefined
                    ? mentionIndex[partner.name] + 1 :
                    0;
                const index = this.composer.textInputContent.indexOf(`@${partner.name}`, fromIndex);
                if (index === -1) {
                    this.update({ mentionedPartners: unlink(partner)});
                }
            }

            // ensure the same mention is not used multiple times if multiple
            // channels have the same name
            const channelIndex = {};
            for (const channel of this.mentionedChannels) {
                const fromIndex = channelIndex[channel.name] !== undefined
                    ? channelIndex[channel.name] + 1 :
                    0;
                const index = this.composer.textInputContent.indexOf(`#${channel.name}`, fromIndex);
                if (index === -1) {
                    this.update({ mentionedChannels: unlink(channel) });
                }
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {FieldCommand}
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
         * @private
         * @returns {boolean}
         */
        _computeIsLog() {
            return this.composer.isLog;
        }

        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThread() {
            return replace(this.composer.thread);
        }

        /**
         * @private
         * @returns {string}
         */
        _computeRawBody() {
            return this.composer.textInputContent;
        }

    }

    MessageComposition.fields = {
        /**
         * States which attachments are currently being created in this message composition.
         */
        attachments: many2many('mail.attachment', {
            inverse: 'messageComposition',
        }),
        /**
         * The body of message resulting from this message composition.
         * It's created when needed to avoid performance issue.
         */
        body: attr(),
        /**
         * States the body without any transformation. It basically the content of
         * the composer.
         */
        rawBody: attr({
            compute: '_computeRawBody',
        }),
        /**
         * States the mentionned channel in the rawBody.
         */
        mentionedChannels: many2many('mail.thread'),
        /**
         * States the mentionned partners in the rawBody.
         */
        mentionedPartners: many2many('mail.partner'),
        thread: one2one('mail.thread', {
            compute: '_computeThread',
        }),
        isLog: attr({
            compute: '_computeIsLog',
        }),
        recipients: many2many('mail.partner', {
            compute: '_computeRecipients',
        }),
        composer: one2one('mail.composer', {
            inverse: 'messageComposition',
            readonly: true,
            required: true,
        }),
    };
    MessageComposition.identifyingFields = ['composer'];
    MessageComposition.modelName = 'mail.message_composition';

    return MessageComposition;
}

registerNewModel('mail.message_composition', factory);
