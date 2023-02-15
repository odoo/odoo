/** @odoo-module **/

import { escape } from "@web/core/utils/strings";

/**
 * This mixin gathers a few methods that are used to handle emojis.
 *
 * It's currently used to format text and wrap the emojis around <span class="o_mail_emoji"> to make them look nicer
 *
 */
export default {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a span with a CSS class around chains of emojis in the message for styling purposes.
     * The input is first passed through 'escape' to prevent unwanted injections into the HTML
     *
     * Sequences of emojis are wrapped instead of individual ones to prevent compound emojis
     * such as 👩🏿 = 👩 + 🏿 [dark skin tone character] from being separated.
     *
     * This will only match characters that have a different presentation from normal text, unlike ®
     * For alternatives, see: https://www.unicode.org/reports/tr51/#Emoji_Properties_and_Data_Files
     *
     * @param {String} message a text message to format
     */
    _formatText(message) {
        message = escape(message);
        message = message.replaceAll(/(\p{Emoji_Presentation}+)/ug, "<span class='o_mail_emoji'>$1</span>");
        message = message.replace(/(?:\r\n|\r|\n)/g, "<br>");

        return message;
    },
};
