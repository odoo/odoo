import { stateToUrl } from "@web/core/browser/router";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";

import { escape, unaccent } from "@web/core/utils/strings";

const urlRegexp =
    /\b(?:https?:\/\/\d{1,3}(?:\.\d{1,3}){3}|(?:https?:\/\/|(?:www\.))[-a-z0-9@:%._+~#=\u00C0-\u024F\u1E00-\u1EFF]{2,256}\.[a-z]{2,13})\b(?:[-a-z0-9@:%_+~#?&[\]^|{}`\\'$//=\u00C0-\u024F\u1E00-\u1EFF]|[.]*[-a-z0-9@:%_+~#?&[\]^|{}`\\'$//=\u00C0-\u024F\u1E00-\u1EFF]|,(?!$| )|\.(?!$| |\.)|;(?!$| ))*/gi;

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
 * @param rawBody {string}
 * @param validRecords {Object}
 * @param validRecords.partners {Partner}
 */
export async function prettifyMessageContent(rawBody, validRecords = []) {
    // Suggested URL Javascript regex of http://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url
    // Adapted to make http(s):// not required if (and only if) www. is given. So `should.notmatch` does not match.
    // And further extended to include Latin-1 Supplement, Latin Extended-A, Latin Extended-B and Latin Extended Additional.
    const escapedAndCompactContent = escapeAndCompactTextContent(rawBody);
    let body = escapedAndCompactContent.replace(/&nbsp;/g, " ").trim();
    // This message will be received from the mail composer as html content
    // subtype but the urls will not be linkified. If the mail composer
    // takes the responsibility to linkify the urls we end up with double
    // linkification a bit everywhere. Ideally we want to keep the content
    // as text internally and only make html enrichment at display time but
    // the current design makes this quite hard to do.
    body = generateMentionsLinks(body, validRecords);
    body = parseAndTransform(body, addLink);
    body = await _generateEmojisOnHtml(body);
    return body;
}

/**
 * WARNING: this is not enough to unescape potential XSS contained in htmlString, transformFunction
 * should handle it or it should be handled after/before calling parseAndTransform. So if the result
 * of this function is used in a t-raw, be very careful.
 *
 * @param {string} htmlString
 * @param {function} transformFunction
 * @returns {string}
 */
export function parseAndTransform(htmlString, transformFunction) {
    const openToken = "OPEN" + Date.now();
    const string = htmlString.replace(/&lt;/g, openToken);
    let children;
    try {
        const div = document.createElement("div");
        div.innerHTML = string; // /!\ quotes are unescaped
        children = Array.from(div.childNodes);
    } catch {
        const div = document.createElement("div");
        div.innerHTML = `<pre>${string}</pre>`;
        children = Array.from(div.childNodes);
    }
    return _parseAndTransform(children, transformFunction).replace(
        new RegExp(openToken, "g"),
        "&lt;"
    );
}

/**
 * @param {Node[]} nodes
 * @param {function} transformFunction with:
 *   param node
 *   param function
 *   return string
 * @return {string}
 */
function _parseAndTransform(nodes, transformFunction) {
    if (!nodes) {
        return;
    }
    return Object.values(nodes)
        .map((node) => {
            return transformFunction(node, function () {
                return _parseAndTransform(node.childNodes, transformFunction);
            });
        })
        .join("");
}

/**
 * @param {string} text
 * @return {string} linkified text
 */
function linkify(text) {
    let curIndex = 0;
    let result = "";
    let match;
    while ((match = urlRegexp.exec(text)) !== null) {
        result += _escapeEntities(text.slice(curIndex, match.index));
        // Decode the url first, in case it's already an encoded url
        const url = decodeURI(match[0]);
        const href = encodeURI(!/^https?:\/\//i.test(url) ? "http://" + url : url);
        result += `<a target="_blank" rel="noreferrer noopener" href="${href}">${_escapeEntities(
            url
        )}</a>`;
        curIndex = match.index + match[0].length;
    }
    return result + _escapeEntities(text.slice(curIndex));
}

export function addLink(node, transformChildren) {
    if (node.nodeType === 3) {
        // text node
        const linkified = linkify(node.data);
        if (linkified !== node.data) {
            const div = document.createElement("div");
            div.innerHTML = linkified;
            for (const childNode of [...div.childNodes]) {
                node.parentNode.insertBefore(childNode, node);
            }
            node.parentNode.removeChild(node);
            return linkified;
        }
        return node.textContent;
    }
    if (node.tagName === "A") {
        return node.outerHTML;
    }
    transformChildren();
    return node.outerHTML;
}

/**
 * Returns an escaped conversion of a content.
 *
 * @param {string} content
 * @returns {string}
 */
export function escapeAndCompactTextContent(content) {
    //Removing unwanted extra spaces from message
    let value = escape(content).trim();
    value = value.replace(/(\r|\n){2,}/g, "<br/><br/>");
    value = value.replace(/(\r|\n)/g, "<br/>");

    // prevent html space collapsing
    value = value.replace(/ /g, "&nbsp;").replace(/([^>])&nbsp;([^<])/g, "$1 $2");
    return value;
}

/**
 * @param body {string}
 * @param validRecords {Object}
 * @param validRecords.partners {Array}
 * @return {string}
 */
function generateMentionsLinks(body, { partners = [], threads = [], specialMentions = [] }) {
    const mentions = [];
    for (const partner of partners) {
        const placeholder = `@-mention-partner-${partner.id}`;
        const text = `@${escape(partner.name)}`;
        mentions.push({
            class: "o_mail_redirect",
            id: partner.id,
            model: "res.partner",
            placeholder,
            text,
        });
        body = body.replace(text, placeholder);
    }
    for (const thread of threads) {
        const placeholder = `#-mention-channel-${thread.id}`;
        let className, text;
        if (thread.parent_channel_id) {
            className = "o_channel_redirect o_channel_redirect_asThread";
            text = escape(`#${thread.parent_channel_id.displayName} > ${thread.displayName}`);
        } else {
            className = "o_channel_redirect";
            text = escape(`#${thread.displayName}`);
        }
        mentions.push({
            class: className,
            id: thread.id,
            model: "discuss.channel",
            placeholder,
            text,
        });
        body = body.replace(text, placeholder);
    }
    for (const special of specialMentions) {
        body = body.replace(
            `@${escape(special)}`,
            `<a href="#" class="o-discuss-mention">@${escape(special)}</a>`
        );
    }
    for (const mention of mentions) {
        const href = `href='${stateToUrl({ model: mention.model, resId: mention.id })}'`;
        const attClass = `class='${mention.class}'`;
        const dataOeId = `data-oe-id='${mention.id}'`;
        const dataOeModel = `data-oe-model='${mention.model}'`;
        const target = "target='_blank'";
        const link = `<a ${href} ${attClass} ${dataOeId} ${dataOeModel} ${target} contenteditable="false">${mention.text}</a>`;
        body = body.replace(mention.placeholder, link);
    }
    return body;
}

/**
 * @private
 * @param {string} htmlString
 * @returns {string}
 */
async function _generateEmojisOnHtml(htmlString) {
    const { emojis } = await loadEmoji();
    for (const emoji of emojis) {
        for (const source of [...emoji.shortcodes, ...emoji.emoticons]) {
            const escapedSource = String(source).replace(/([.*+?=^!:${}()|[\]/\\])/g, "\\$1");
            const regexp = new RegExp("(\\s|^)(" + escapedSource + ")(?=\\s|$)", "g");
            htmlString = htmlString.replace(regexp, "$1" + emoji.codepoints);
        }
    }
    return htmlString;
}

export function htmlToTextContentInline(htmlString) {
    const fragment = document.createDocumentFragment();
    const div = document.createElement("div");
    fragment.appendChild(div);
    htmlString = htmlString.replace(/<br\s*\/?>/gi, " ");
    try {
        div.innerHTML = htmlString;
    } catch {
        div.innerHTML = `<pre>${htmlString}</pre>`;
    }
    return div.textContent
        .trim()
        .replace(/[\n\r]/g, "")
        .replace(/\s\s+/g, " ");
}

export function convertBrToLineBreak(str) {
    return new DOMParser().parseFromString(
        str.replaceAll("<br>", "\n").replaceAll("</br>", "\n"),
        "text/html"
    ).body.textContent;
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
