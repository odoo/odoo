/** @odoo-module **/

import { emojis } from '@mail/js/emojis';
import { registerModel } from '@mail/model/model_core';
import { unlink } from '@mail/model/model_field_command';
import { attr, many, one } from '@mail/model/model_field';
import { addLink, escapeAndCompactTextContent, parseAndTransform } from '@mail/js/utils';

import { escape } from '@web/core/utils/strings';

/**
 * Model of a message being composed in a composer.
 *
 * Note that a message composition is not a full-fledged message, because it
 * hasn't been posted yet.
 * Still, it looks somewhat like a message, which is intended because when a
 * message composition is posted, it becomes a message.
 */
registerModel({
    name: 'MessageComposition',
    identifyingFields: ['id'],
    recordMethods: {
        /**
         * This method will generate the html body of a message, create the
         * link, mention link, channel link, and convert the emoji's.
         * This is intentionally NOT a compute to avoid possible performance issue.
         *
         * @return void
         */
        generateBody() {
            const escapedAndCompactContent = escapeAndCompactTextContent(this.message.body);
            let body = escapedAndCompactContent.replace(/&nbsp;/g, ' ').trim();
            // This message will be received from the mail composer as html content
            // subtype but the urls will not be linkified. If the mail composer
            // takes the responsibility to linkify the urls we end up with double
            // linkification a bit everywhere. Ideally we want to keep the content
            // as text internally and only make html enrichment at display time but
            // the current design makes this quite hard to do.
            this._cleanMentionedPartners();
            this._cleanMentionedChannels();
            body = this._generateMentionsLinks(body);
            body = parseAndTransform(body, addLink);
            body = this._generateEmojisOnHtml(body);
            this.message.update({ body });
        },
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
            for (const channel of this.mentionedChannels) {
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
         * Detects if mentioned channels are still in the composer text input content
         * and removes them if not.
         *
         * @private
         * @returns {Partner[]}
         */
        _cleanMentionedChannels() {
            const unmentionedChannels = [];
            // ensure the same mention is not used multiple times if multiple
            // channels have the same name
            const namesIndex = {};
            for (const channel of this.mentionedChannels) {
                const fromIndex = namesIndex[channel.name] !== undefined
                    ? namesIndex[channel.name] + 1 :
                    0;
                const index = this.message.body.indexOf(`#${channel.name}`, fromIndex);
                if (index !== -1) {
                    namesIndex[channel.name] = index;
                } else {
                    unmentionedChannels.push(channel);
                }
            }
            this.update({ mentionedChannels: unlink(unmentionedChannels) });
        },
        /**
         * Detects if mentioned partners are still in the composer text input content
         * and removes them if not.
         *
         * @private
         * @returns {Partner[]}
         */
        _cleanMentionedPartners() {
            const unmentionedPartners = [];
            // ensure the same mention is not used multiple times if multiple
            // partners have the same name
            const namesIndex = {};
            for (const partner of this.mentionedPartners) {
                const fromIndex = namesIndex[partner.name] !== undefined
                    ? namesIndex[partner.name] + 1 :
                    0;
                const index = this.message.body.indexOf(`@${partner.name}`, fromIndex);
                if (index !== -1) {
                    namesIndex[partner.name] = index;
                } else {
                    unmentionedPartners.push(partner);
                }
            }
            this.update({ mentionedPartners: unlink(unmentionedPartners) });
        },
    },
    fields: {
        id: attr({
            readonly: true,
            required: true,
        }),
        /**
         * The body of message resulting from this message composition.
         * It's created when needed to avoid performance issue.
         */
        body: attr(),
        composerView: one('ComposerView'),
        isLog: attr({
            default: false
        }),
        /**
         * States the mentionned channel in the body.
         */
        mentionedChannels: many('Thread'),
        /**
         * States the mentionned partners in the body.
         */
        mentionedPartners: many('Partner'),
        /**
         * States the body without any transformation. It basically the content of
         * the composer.
         */
        message: one('Message', {
            inverse: 'messageComposition',
        }),
        rawBody: attr(),
        recipients: many('Partner'),
    }
});
