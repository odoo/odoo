/* @odoo-module */

import { escape, unaccent } from "@web/core/utils/strings";
import { url } from "@web/core/utils/urls";
import { loadEmoji } from "@mail/emoji_picker/emoji_picker";

const urlRegexp =
    /\b(?:https?:\/\/\d{1,3}(?:\.\d{1,3}){3}|(?:https?:\/\/|(?:www\.))[-a-z0-9@:%._+~#=\u00C0-\u024F\u1E00-\u1EFF]{2,256}\.[a-z]{2,13})\b(?:[-a-z0-9@:%_+.~#?&'$//=;\u00C0-\u024F\u1E00-\u1EFF]*)/gi;

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
function parseAndTransform(htmlString, transformFunction) {
    const openToken = "OPEN" + Date.now();
    const string = htmlString.replace(/&lt;/g, openToken);
    let children;
    try {
        children = $("<div>").html(string).contents();
    } catch {
        children = $("<div>")
            .html("<pre>" + string + "</pre>")
            .contents();
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
 * @param {Object} [attrs={}]
 * @return {string} linkified text
 */
function linkify(text, attrs) {
    attrs = attrs || {};
    if (attrs.target === undefined) {
        attrs.target = "_blank";
    }
    if (attrs.target === "_blank") {
        attrs.rel = "noreferrer noopener";
    }
    attrs = Object.keys(attrs)
        .map(function (key) {
            return key + '="' + escape(attrs[key]) + '"';
        })
        .join(" ");
    return text.replace(urlRegexp, function (url) {
        var href = !/^https?:\/\//i.test(url) ? "http://" + url : url;
        return "<a " + attrs + ' href="' + href + '">' + url + "</a>";
    });
}

function addLink(node, transformChildren) {
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
function generateMentionsLinks(body, { partners = [], threads = [] }) {
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
        const text = `#${escape(thread.displayName)}`;
        mentions.push({
            class: "o_channel_redirect",
            id: thread.id,
            model: "discuss.channel",
            placeholder,
            text,
        });
        body = body.replace(text, placeholder);
    }
    const baseHREF = url("/web");
    for (const mention of mentions) {
        const href = `href='${baseHREF}#model=${mention.model}&id=${mention.id}'`;
        const attClass = `class='${mention.class}'`;
        const dataOeId = `data-oe-id='${mention.id}'`;
        const dataOeModel = `data-oe-model='${mention.model}'`;
        const target = "target='_blank'";
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
    return unaccent(term.toLowerCase());
}
