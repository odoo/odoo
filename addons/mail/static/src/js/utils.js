/* @odoo-module */

import { escape } from "@web/core/utils/strings";

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
    var openToken = "OPEN" + Date.now();
    var string = htmlString.replace(/&lt;/g, openToken);
    var children;
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
    return Array.from($(nodes))
        .map((node) => {
            return transformFunction(node, function () {
                return _parseAndTransform(node.childNodes, transformFunction);
            });
        })
        .join("");
}

/**
 * Escape < > & as html entities (copy from underscore escape function with less escaped characters)
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

// Suggested URL Javascript regex of http://stackoverflow.com/questions/3809401/what-is-a-good-regular-expression-to-match-a-url
// Adapted to make http(s):// not required if (and only if) www. is given. So `should.notmatch` does not match.
// And further extended to include Latin-1 Supplement, Latin Extended-A, Latin Extended-B and Latin Extended Additional.
const urlRegexp =
    /\b(?:https?:\/\/\d{1,3}(?:\.\d{1,3}){3}|(?:https?:\/\/|(?:www\.))[-a-z0-9@:%._+~#=\u00C0-\u024F\u1E00-\u1EFF]{2,256}\.[a-z]{2,13})\b(?:[-a-z0-9@:%_+~#?&[\]^|{}`\\'$//=\u00C0-\u024F\u1E00-\u1EFF]|,(?!$| )|\.(?!$| |\.)|;(?!$| ))*/gi;

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
    attrs = Object.keys(attrs || {})
        .map((key) => {
            const value = attrs[key];
            return `${key}="${escape(value)}"`;
        })
        .join(" ");
    let curIndex = 0;
    let result = "";
    let match;
    while ((match = urlRegexp.exec(text)) !== null) {
        result += _escapeEntities(text.slice(curIndex, match.index));
        const url = match[0];
        const href = !/^https?:\/\//i.test(url) ? "http://" + encodeURI(url) : encodeURI(url);
        result += "<a " + attrs + ' href="' + href + '">' + _escapeEntities(url) + "</a>";
        curIndex = match.index + match[0].length;
    }
    return result + _escapeEntities(text.slice(curIndex));
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
 * @param {string} htmlString
 * @return {string}
 */
function htmlToTextContentInline(htmlString) {
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

function stripHTML(node, transformChildren) {
    if (node.nodeType === 3) {
        return node.data;
    } // text node
    if (node.tagName === "BR") {
        return "\n";
    }
    return transformChildren();
}

function inline(node, transform_children) {
    if (node.nodeType === 3) {
        return node.data;
    }
    if (node.nodeType === 8) {
        return "";
    }
    if (node.tagName === "BR") {
        return " ";
    }
    if (node.tagName.match(/^(A|P|DIV|PRE|BLOCKQUOTE)$/)) {
        return transform_children();
    }
    node.innerHTML = transform_children();
    return node.outerHTML;
}

// Parses text to find email: Tagada <address@mail.fr> -> [Tagada, address@mail.fr] or False
function parseEmail(text) {
    if (text) {
        var result = text.match(/"?(.*?)"? <(.*@.*)>/);
        if (result) {
            name = (result[1] || "").trim().replace(/(^"|"$)/g, '')
            return [name, (result[2] || "").trim()];
        }
        result = text.match(/(.*@.*)/);
        if (result) {
            return [String(result[1] || "").trim(), String(result[1] || "").trim()];
        }
        return [text, false];
    }
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

// Replaces textarea text into html text (add <p>, <a>)
// TDE note : should be done server-side, in Python -> use mail.compose.message ?
function getTextToHTML(text) {
    return text
        .replace(/((?:https?|ftp):\/\/[\S]+)/g, '<a href="$1">$1</a> ')
        .replace(/[\n\r]/g, "<br/>");
}

export {
    addLink,
    escapeAndCompactTextContent,
    getTextToHTML,
    htmlToTextContentInline,
    inline,
    linkify,
    parseAndTransform,
    parseEmail,
    stripHTML,
};
