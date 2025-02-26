import { Markup } from "@web/core/utils/html";

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
    message = Markup.replaceAll(
        message,
        /(\p{Emoji_Presentation}+)/gu,
        Markup.build`<span class='o_mail_emoji'>$1</span>`
    );
    message = Markup.replace(message, /(?:\r\n|\r|\n)/g, Markup.build`<br>`);
    return message;
}
