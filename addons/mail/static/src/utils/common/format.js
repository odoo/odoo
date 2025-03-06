import {
    createDocumentFragmentFromContent,
    htmlJoin,
    htmlReplace,
    htmlTrim,
} from "@mail/utils/common/html";

import { markup } from "@odoo/owl";

import { stateToUrl } from "@web/core/browser/router";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { htmlEscape, setElementContent } from "@web/core/utils/html";
import { escapeRegExp, unaccent } from "@web/core/utils/strings";
import { setAttributes } from "@web/core/utils/xml";

const urlRegexp =
    /\b(?:https?:\/\/\d{1,3}(?:\.\d{1,3}){3}|(?:https?:\/\/|(?:www\.))[-a-z0-9@:%._+~#=\u00C0-\u024F\u1E00-\u1EFF]{1,256}\.[a-z]{2,13})\b(?:[-a-z0-9@:%_+~#?&[\]^|{}`\\'$//=\u00C0-\u024F\u1E00-\u1EFF]|[.]*[-a-z0-9@:%_+~#?&[\]^|{}`\\'$//=\u00C0-\u024F\u1E00-\u1EFF]|,(?!$| )|\.(?!$| |\.)|;(?!$| ))*/gi;

/**
 * Escape < > & as html entities
 *
 * @param {string}
 * @return {string}
 */
const _escapeEntities = (function () {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;" };
    const escaper = function (match) {
        return map[match];
    };
    const testRegexp = RegExp("(?:&|<|>)");
    const replaceRegexp = RegExp("(?:&|<|>)", "g");
    return function (string) {
        string = string == null ? "" : "" + string;
        return testRegexp.test(string) ? string.replace(replaceRegexp, escaper) : string;
    };
})();

/**
 * @param rawBody {string|ReturnType<markup>}
 * @param validRecords {Object}
 * @param validRecords.partners {Partner}
 */
export async function prettifyMessageContent(rawBody, validRecords = []) {
    // Suggested URL Javascript regex of http://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url
    // Adapted to make http(s):// not required if (and only if) www. is given. So `should.notmatch` does not match.
    // And further extended to include Latin-1 Supplement, Latin Extended-A, Latin Extended-B and Latin Extended Additional.
    const escapedAndCompactContent = escapeAndCompactTextContent(rawBody);
    let body = htmlReplace(escapedAndCompactContent, /&nbsp;/g, " ");
    body = htmlTrim(body);
    // This message will be received from the mail composer as html content
    // subtype but the urls will not be linkified. If the mail composer
    // takes the responsibility to linkify the urls we end up with double
    // linkification a bit everywhere. Ideally we want to keep the content
    // as text internally and only make html enrichment at display time but
    // the current design makes this quite hard to do.
    body = generateMentionsLinks(body, validRecords);
    body = await _generateEmojisOnHtml(body);
    body = parseAndTransform(body, addLink);
    return body;
}

/**
 * WARNING: this is not enough to unescape potential XSS contained in htmlString, transformFunction
 * should handle it or it should be handled after/before calling parseAndTransform. So if the result
 * of this function is used in a t-raw, be very careful.
 *
 * @param {string|ReturnType<markup>} htmlString
 * @param {function} transformFunction
 * @returns {ReturnType<markup>}
 */
export function parseAndTransform(htmlString, transformFunction) {
    let children;
    try {
        const div = document.createElement("div");
        setElementContent(div, htmlString);
        children = Array.from(div.childNodes);
    } catch {
        const div = document.createElement("div");
        const pre = document.createElement("pre");
        setElementContent(pre, htmlString);
        div.appendChild(pre);
        children = Array.from(div.childNodes);
    }
    return _parseAndTransform(children, transformFunction);
}

/**
 * @param {Node[]} nodes
 * @param {function} transformFunction with:
 *   param node
 *   param function
 *   return string
 * @return {ReturnType<markup>}
 */
function _parseAndTransform(nodes, transformFunction) {
    if (!nodes) {
        return;
    }
    return htmlJoin(
        ...Object.values(nodes).map((node) =>
            transformFunction(node, function () {
                return _parseAndTransform(node.childNodes, transformFunction);
            })
        )
    );
}

/**
 * @param {string} text
 * @return {ReturnType<markup>} linkified text
 */
function linkify(text) {
    let curIndex = 0;
    let result = "";
    let match;
    while ((match = urlRegexp.exec(text)) !== null) {
        result = htmlJoin(result, text.slice(curIndex, match.index));
        // Decode the url first, in case it's already an encoded url
        const url = decodeURI(match[0]);
        const href = encodeURI(!/^https?:\/\//i.test(url) ? "http://" + url : url);
        result = htmlJoin(
            result,
            markup(
                `<a target="_blank" rel="noreferrer noopener" href="${href}">${_escapeEntities(
                    url
                )}</a>`
            )
        );
        curIndex = match.index + match[0].length;
    }
    return htmlJoin(result, text.slice(curIndex));
}

/**
 * @param {Node} node
 * @param {function} transformFunction
 * @return {ReturnType<markup>}
 */
export function addLink(node, transformChildren) {
    if (node.nodeType === 3) {
        // text node
        const linkified = linkify(node.textContent);
        if (linkified.toString() !== node.textContent) {
            const div = document.createElement("div");
            setElementContent(div, linkified);
            for (const childNode of [...div.childNodes]) {
                node.parentNode.insertBefore(childNode, node);
            }
            node.parentNode.removeChild(node);
            return linkified;
        }
        return node.textContent;
    }
    if (node.tagName === "A") {
        return markup(node.outerHTML);
    }
    transformChildren();
    return markup(node.outerHTML);
}

/**
 * Returns an escaped conversion of a content.
 *
 * @param {string|ReturnType<markup>} content
 * @returns {ReturnType<markup>}
 */
export function escapeAndCompactTextContent(content) {
    //Removing unwanted extra spaces from message
    let value = htmlTrim(content);
    value = htmlReplace(value, /(\r|\n){2,}/g, markup("<br/><br/>"));
    value = htmlReplace(value, /(\r|\n)/g, markup("<br/>"));

    // prevent html space collapsing
    value = htmlReplace(value, / /g, markup("&nbsp;"));
    value = htmlReplace(value, /([^>])&nbsp;([^<])/g, markup("$1 $2"));
    return value;
}

/**
 * @param body {string|ReturnType<markup>}
 * @param validRecords {Object}
 * @param validRecords.partners {Array}
 * @return {ReturnType<markup>}
 */
function generateMentionsLinks(body, { partners = [], threads = [], specialMentions = [] }) {
    const mentions = [];
    for (const partner of partners) {
        const placeholder = `@-mention-partner-${partner.id}`;
        const text = `@${partner.name}`;
        mentions.push({
            class: "o_mail_redirect",
            id: partner.id,
            model: "res.partner",
            placeholder,
            text,
        });
        body = htmlReplace(body, text, placeholder);
    }
    for (const thread of threads) {
        const placeholder = `#-mention-channel-${thread.id}`;
        let className, text;
        if (thread.parent_channel_id) {
            className = "o_channel_redirect o_channel_redirect_asThread";
            text = `#${thread.parent_channel_id.displayName} > ${thread.displayName}`;
        } else {
            className = "o_channel_redirect";
            text = `#${thread.displayName}`;
        }
        mentions.push({
            class: className,
            id: thread.id,
            model: "discuss.channel",
            placeholder,
            text,
        });
        body = htmlReplace(body, text, placeholder);
    }
    for (const special of specialMentions) {
        body = htmlReplace(
            body,
            `@${special}`,
            markup(`<a href="#" class="o-discuss-mention">@${htmlEscape(special)}</a>`)
        );
    }
    for (const mention of mentions) {
        const link = document.createElement("a");
        setAttributes(link, {
            href: stateToUrl({ model: mention.model, resId: mention.id }),
            class: mention.class,
            "data-oe-id": mention.id,
            "data-oe-model": mention.model,
            target: "_blank",
            contenteditable: "false",
        });
        link.textContent = mention.text;
        body = htmlReplace(body, mention.placeholder, markup(link.outerHTML));
    }
    return htmlEscape(body);
}

/**
 * @private
 * @param {string|ReturnType<markup>} htmlString
 * @returns {ReturnType<markup>}
 */
async function _generateEmojisOnHtml(htmlString) {
    const { emojis } = await loadEmoji();
    for (const emoji of emojis) {
        for (const source of [...emoji.shortcodes, ...emoji.emoticons]) {
            const escapedSource = htmlJoin(String(source));
            const regexp = new RegExp("(\\s|^)(" + escapeRegExp(escapedSource) + ")(?=\\s|$)", "g");
            htmlString = htmlReplace(htmlString, regexp, "$1" + emoji.codepoints);
        }
    }
    return htmlEscape(htmlString);
}

/**
 * @param {string|ReturnType<markup>} htmlString
 * @returns {string}
 */
export function htmlToTextContentInline(htmlString) {
    htmlString = htmlReplace(htmlString, /<br\s*\/?>/gi, " ");
    const div = document.createElement("div");
    try {
        setElementContent(div, htmlString);
    } catch {
        const pre = document.createElement("pre");
        setElementContent(pre, htmlString);
        div.appendChild(pre);
    }
    return div.textContent
        .trim()
        .replace(/[\n\r]/g, "")
        .replace(/\s\s+/g, " ");
}

export function convertBrToLineBreak(str) {
    str = htmlReplace(str, /<br\s*\/?>/gi, "\n");
    return createDocumentFragmentFromContent(str).body.textContent;
}

export function cleanTerm(term) {
    return unaccent((typeof term === "string" ? term : "").toLowerCase());
}

/**
 * Parses text to find email: Tagada <address@mail.fr> -> [Tagada, address@mail.fr] or False
 *
 * @param {string} text
 * @returns {[string,string|boolean]|false}
 */
export function parseEmail(text) {
    if (!text) {
        return;
    }
    let result = text.match(/"?(.*?)"? <(.*@.*)>/);
    if (result) {
        const name = (result[1] || "").trim().replace(/(^"|"$)/g, "");
        return [name, (result[2] || "").trim()];
    }
    result = text.match(/(.*@.*)/);
    if (result) {
        return [String(result[1] || "").trim(), String(result[1] || "").trim()];
    }
    return [text, false];
}

export const EMOJI_REGEX = /\p{Emoji_Presentation}|\p{Emoji}\uFE0F|\u200d/gu;
