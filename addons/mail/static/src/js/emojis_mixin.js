import { htmlReplace, htmlReplaceAll } from "@mail/utils/common/html";

import { markup } from "@odoo/owl";

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
 * @param {string|ReturnType<markup>} message a text message to format
 * @returns {ReturnType<markup>}
 */
export function formatText(message) {
    message = htmlReplaceAll(
        message,
        /(\p{Emoji_Presentation}+)/gu,
        (_, group1) => markup`<span class='o_mail_emoji'>${group1}</span>`
    );
    message = htmlReplace(message, /(?:\r\n|\r|\n)/g, () => markup`<br>`);
    return message;
}
