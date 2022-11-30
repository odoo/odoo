/** @odoo-module **/

import { loadEmoji } from "@mail/new/utils/emoji/emoji_picker";

import { escape } from "@web/core/utils/strings";

const urlRegexp =
    /\b(?:https?:\/\/\d{1,3}(?:\.\d{1,3}){3}|(?:https?:\/\/|(?:www\.))[-a-z0-9@:%._+~#=\u00C0-\u024F\u1E00-\u1EFF]{2,256}\.[a-z]{2,13})\b(?:[-a-z0-9@:%_+.~#?&'$//=;\u00C0-\u024F\u1E00-\u1EFF]*)/gi;

/**
 * @param rawBody {string}
 */
export async function prettifyMessageContent(rawBody) {
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
    // body = this._generateMentionsLinks(body);
    body = parseAndTransform(body, addLink);
    body = _generateEmojisOnHtml(body);
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
function escapeAndCompactTextContent(content) {
    //Removing unwanted extra spaces from message
    let value = escape(content).trim();
    value = value.replace(/(\r|\n){2,}/g, "<br/><br/>");
    value = value.replace(/(\r|\n)/g, "<br/>");

    // prevent html space collapsing
    value = value.replace(/ /g, "&nbsp;").replace(/([^>])&nbsp;([^<])/g, "$1 $2");
    return value;
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
