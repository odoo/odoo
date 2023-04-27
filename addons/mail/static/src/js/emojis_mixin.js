odoo.define('mail.emoji_mixin', function (require) {
"use strict";

var emojis = require('mail.emojis');

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
return {
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
    _onEmojiClick: function (ev) {
        var unicode = ev.currentTarget.textContent.trim();
        var textInput = this._getTargetTextElement($(ev.currentTarget))[0];
        var selectionStart = textInput.selectionStart;

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
    _formatText: function (message) {
        message = this._htmlEscape(message);
        message = this._wrapEmojis(message);
        message = message.replace(/(?:\r\n|\r|\n)/g, '<br>');

        return message;
    },

    /**
     * Adapted from qweb2.js#html_escape to avoid formatting '&'
     *
     * @param {String} s
     * @private
     */
    _htmlEscape: function (s) {
        if (s == null) {
            return '';
        }
        return String(s).replace(/</g, '&lt;').replace(/>/g, '&gt;');
    },

    /**
     * Will use the mail.emojis library to wrap emojis unicode around a span with a special font
     * that will make them look nicer (colored, ...).
     *
     * @param {String} message
     */
    _wrapEmojis: function (message) {
        emojis.forEach(function (emoji) {
            message = message.replace(
                new RegExp(emoji.unicode.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'),
                '<span class="o_mail_emoji">' + emoji.unicode + '</span>'
            );
        });

        return message;
    }
};

});
