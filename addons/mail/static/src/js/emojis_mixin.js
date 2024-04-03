/** @odoo-module **/

import { escape } from '@web/core/utils/strings';
import emojis from '@mail/js/emojis';

/**
 * This mixin gathers a few methods that are used to handle emojis.
 *
 * It's used to:
 *
 * - handle the click on an emoji from a dropdown panel and add it to the related textarea/input
 * - format text and wrap the emojis around <span class="o_mail_emoji"> to make them look nicer
 *
 * Methods are based on the collections of emojis available in mail.emojis
 *
 */
export default {
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This method should be bound to a click event on an emoji.
     * (used in text element's emojis dropdown list)
     *
     * It assumes that a ``_getTargetTextElement`` method is defined that will return the related
     * textarea/input element in which the emoji will be inserted.
     *
     * @param {MouseEvent} ev
     */
    onEmojiClick(ev) {
        const unicode = ev.currentTarget.textContent.trim();
        const textInput = this._getTargetTextElement($(ev.currentTarget));
        const selectionStart = textInput.selectionStart;

        textInput.value = textInput.value.slice(0, selectionStart) + unicode + textInput.value.slice(selectionStart);
        textInput.focus();
        textInput.setSelectionRange(selectionStart + unicode.length, selectionStart + unicode.length);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This method is used to wrap emojis in a text message with <span class="o_mail_emoji">
     * As this returns html to be used in a 't-raw' argument, it first makes sure that the
     * passed text message is html escaped for safety reasons.
     *
     * @param {String} message a text message to format
     */
    _formatText(message) {
        message = escape(message);
        message = this._wrapEmojis(message);
        message = message.replace(/(?:\r\n|\r|\n)/g, '<br>');

        return message;
    },

    /**
     * Will use the mail.emojis library to wrap emojis unicode around a span with a special font
     * that will make them look nicer (colored, ...).
     *
     * @param {String} message
     */
    _wrapEmojis(message) {
        emojis.forEach(function (emoji) {
            message = message.replace(
                new RegExp(emoji.unicode.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'),
                '<span class="o_mail_emoji">' + emoji.unicode + '</span>'
            );
        });

        return message;
    }
};
