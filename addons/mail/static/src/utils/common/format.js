import { htmlEscape, markup } from "@odoo/owl";

import { router } from "@web/core/browser/router";
import { loadEmoji, loader } from "@web/core/emoji_picker/emoji_picker";
import { normalize } from "@web/core/l10n/utils";
import {
    createDocumentFragmentFromContent,
    createElementWithContent,
    htmlFormatList,
    htmlJoin,
    htmlReplace,
    htmlReplaceAll,
    htmlTrim,
    setElementContent,
} from "@web/core/utils/html";
import { escapeRegExp } from "@web/core/utils/strings";
import { getOrigin } from "@web/core/utils/urls";
import { setAttributes } from "@web/core/utils/xml";

const urlRegexp =
    /\b(?:https?:\/\/\d{1,3}(?:\.\d{1,3}){3}|(?:https?:\/\/|(?:www\.))[-a-z0-9@:%._+~#=\u00C0-\u024F\u1E00-\u1EFF]{1,256}\.[a-z]{2,13})\b(?:[-a-z0-9@:%_+~#?&[\]^|{}`\\'$//=\u00C0-\u024F\u1E00-\u1EFF]|[.]*[-a-z0-9@:%_+~#?&[\]^|{}`\\'$//=\u00C0-\u024F\u1E00-\u1EFF]|,(?!$| )|\.(?!$| |\.)|;(?!$| ))*/gi;
const messageUrlRegExp = new RegExp(`^${escapeRegExp(getOrigin())}/mail/message/(\\d+)$`);

/**
 * @param {string|ReturnType<markup>} rawBody
 * @param {Object} validMentions
 * @param {import("models").Persona[]} validMentions.partners
 * @returns {Promise<string|ReturnType<markup>>}
 */
export function prettifyMessageText(rawBody, { validMentions = [] } = {}) {
    if (rawBody instanceof markup().constructor) {
        // markup is already "pretty"
        return rawBody;
    }
    let body = htmlTrim(rawBody);
    body = htmlReplace(body, /(\r|\n){2,}/g, () => markup`<br/><br/>`);
    body = htmlReplace(body, /(\r|\n)/g, () => markup`<br/>`);
    body = htmlReplace(body, /&nbsp;/g, () => " ");
    body = htmlTrim(body);
    // This message will be received from the mail composer as html content
    // subtype but the urls will not be linkified. If the mail composer
    // takes the responsibility to linkify the urls we end up with double
    // linkification a bit everywhere. Ideally we want to keep the content
    // as text internally and only make html enrichment at display time but
    // the current design makes this quite hard to do.
    body = generateMentionsLinks(body, validMentions);
    body = parseAndTransform(body, addLink);
    return body;
}

/**
 * @param {string|ReturnType<markup>} htmlBody
 */
export async function generateEmojisOnHtml(htmlBody, { allowEmojiLoading = true } = {}) {
    let body = htmlBody;
    if (allowEmojiLoading || odoo.loader.modules.get("@web/core/emoji_picker/emoji_data")) {
        body = await _generateEmojisOnHtml(body);
    }
    return body;
}

/**
 * @param {string|ReturnType<markup>} rawBody
 * @param {Object} validMentions
 * @param {import("models").Persona[]} validMentions.partners
 */
export async function prettifyMessageContent(
    rawBody,
    { validMentions = [], allowEmojiLoading = true } = {}
) {
    let body = prettifyMessageText(rawBody, { validMentions });
    body = await generateEmojisOnHtml(body, { allowEmojiLoading });
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
    const div = document.createElement("div");
    try {
        setElementContent(div, htmlString);
    } catch {
        div.appendChild(createElementWithContent("pre", htmlString));
    }
    return _parseAndTransform(Array.from(div.childNodes), transformFunction);
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
        Object.values(nodes).map((node) =>
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
        result = htmlJoin([result, text.slice(curIndex, match.index)]);
        // Decode the url first, in case it's already an encoded url
        const inputUrl = decodeURI(match[0]);
        const url = !/^https?:\/\//i.test(inputUrl) ? "http://" + inputUrl : inputUrl;
        const link = document.createElement("a");
        setAttributes(link, {
            target: "_blank",
            rel: "noreferrer noopener",
            href: encodeURI(url),
        });
        link.textContent = inputUrl;
        const messageMatch = messageUrlRegExp.exec(url);
        if (messageMatch !== null) {
            setAttributes(link, {
                "data-oe-id": messageMatch[1],
                "data-oe-model": "mail.message",
            });
            link.classList.add("o_message_redirect");
        }
        // markup: outerHTML is safe when used as a node
        result = htmlJoin([result, markup(link.outerHTML)]);
        curIndex = match.index + match[0].length;
    }
    return htmlJoin([result, text.slice(curIndex)]);
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
            const div = createElementWithContent("div", linkified);
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

function generateMentionElement({ className, id, model, text }) {
    const link = document.createElement("a");
    setAttributes(link, {
        href: router.stateToUrl({ model: model, resId: id }),
        class: className,
        "data-oe-id": id,
        "data-oe-model": model,
        target: "_blank",
        contenteditable: "false",
    });
    link.textContent = text;
    return link;
}

/** @param {import("models").ResPartner} partner */
export function generatePartnerMentionElement(partner) {
    return generateMentionElement({
        className: "o_mail_redirect",
        id: partner.id,
        model: "res.partner",
        text: `@${partner.name}`,
    });
}

/** @param {import("models").ResRole} role */
export function generateRoleMentionElement(role) {
    return generateMentionElement({
        className: "o-discuss-mention",
        id: role.id,
        model: "res.role",
        text: `@${role.name}`,
    });
}

/** @param {string} label */
export function generateSpecialMentionElement(label) {
    const link = document.createElement("a");
    setAttributes(link, {
        class: "o-discuss-mention",
        contenteditable: "false",
    });
    link.textContent = `@${label}`;
    return link;
}

/** @param {import("models").Thread} thread */
export function generateThreadMentionElement(thread) {
    return generateMentionElement({
        className: `o_channel_redirect${
            thread.parent_channel_id ? " o_channel_redirect_asThread" : ""
        }`,
        id: thread.id,
        model: "discuss.channel",
        text: `#${thread.fullNameWithParent}`,
    });
}

/**
 * @param body {string|ReturnType<markup>}
 * @param validRecords {Object}
 * @param validRecords.partners {Array}
 * @return {ReturnType<markup>}
 */
function generateMentionsLinks(
    body,
    { partners = [], roles = [], threads = [], specialMentions = [] }
) {
    const mentions = [];
    for (const partner of partners) {
        const placeholder = `@-mention-partner-${partner.id}`;
        const text = `@${partner.name}`;
        mentions.push({
            link: generatePartnerMentionElement(partner),
            placeholder,
        });
        body = htmlReplace(body, text, placeholder);
    }
    for (const thread of threads) {
        const placeholder = `#-mention-channel-${thread.id}`;
        const text = `#${thread.fullNameWithParent}`;
        mentions.push({
            link: generateThreadMentionElement(thread),
            placeholder,
        });
        body = htmlReplace(body, text, placeholder);
    }
    for (const special of specialMentions) {
        const text = `@${special}`;
        const placeholder = `@-mention-special-${special}`;
        mentions.push({
            link: generateSpecialMentionElement(special),
            placeholder,
        });
        body = htmlReplace(body, text, placeholder);
    }
    for (const role of roles) {
        const placeholder = `@-mention-role-${role.id}`;
        const text = `@${role.name}`;
        mentions.push({
            link: generateRoleMentionElement(role),
            placeholder,
        });
        body = htmlReplace(body, text, placeholder);
    }
    for (const mention of mentions) {
        const link = mention.link;
        // markup: outerHTML is safe when used as a node
        body = htmlReplace(body, mention.placeholder, markup(link.outerHTML));
    }
    return htmlEscape(body);
}

/**
 * @private
 * @param {string|ReturnType<markup>} htmlString
 * @returns {Promise<ReturnType<markup>>}
 */
async function _generateEmojisOnHtml(htmlString) {
    const { emojis } = await loadEmoji();
    for (const emoji of emojis) {
        for (const source of [...emoji.shortcodes, ...emoji.emoticons]) {
            const escapedSource = htmlEscape(String(source));
            const regexp = new RegExp("(\\s|^)(" + escapeRegExp(escapedSource) + ")(?=\\s|$)", "g");
            htmlString = htmlReplace(htmlString, regexp, (_, group1) => group1 + emoji.codepoints);
        }
    }
    return htmlEscape(htmlString);
}

/**
 * @param {string|ReturnType<markup>} body
 * @returns {ReturnType<markup>}
 */
export function getNonEditableMentions(body) {
    const doc = createDocumentFragmentFromContent(body);
    for (const block of doc.body.querySelectorAll(".o_mail_reply_hide")) {
        block.classList.remove("o_mail_reply_hide");
    }
    // for mentioned partner
    for (const mention of doc.body.querySelectorAll(".o_mail_redirect")) {
        mention.setAttribute("contenteditable", false);
    }
    // for mentioned channel
    for (const mention of doc.body.querySelectorAll(".o_channel_redirect")) {
        mention.setAttribute("contenteditable", false);
    }
    // for special mentions
    for (const mention of doc.body.querySelectorAll(".o-discuss-mention")) {
        mention.setAttribute("contenteditable", false);
    }
    return markup(doc.body.innerHTML);
}

/**
 * @param {string|ReturnType<markup>} htmlString
 * @returns {string}
 */
export function htmlToTextContentInline(htmlString) {
    htmlString = htmlReplace(htmlString, /<br\s*\/?>/gi, () => " ");
    const div = document.createElement("div");
    try {
        setElementContent(div, htmlString);
    } catch {
        div.appendChild(createElementWithContent("pre", htmlString));
    }
    return div.textContent
        .trim()
        .replace(/[\n\r]/g, "")
        .replace(/\s\s+/g, " ");
}

export function convertBrToLineBreak(str) {
    str = htmlReplace(str, /<br\s*\/?>/gi, () => "\n");
    return createDocumentFragmentFromContent(str).body.textContent;
}

export function cleanTerm(term) {
    return typeof term === "string" ? normalize(term) : "";
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

/**
 * Wrap emojis present in the given text with a title and return a safe HTML
 * string.
 *
 * @param {string|ReturnType<markup>} content
 * @returns {ReturnType<markup>}
 */
export function decorateEmojis(content) {
    if (!loader.loaded || !content) {
        return content;
    }
    const doc = createDocumentFragmentFromContent(content);
    const nodes = doc.evaluate(
        ".//text()",
        doc.body,
        null,
        XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE,
        null
    );
    for (let i = 0; i < nodes.snapshotLength; i++) {
        const node = nodes.snapshotItem(i);
        const span = document.createElement("span");
        setElementContent(
            span,
            htmlReplaceAll(node.textContent, loader.loaded.emojiRegex, (codepoints) =>
                markup(
                    `<span class="o-mail-emoji" title="${htmlFormatList(
                        loader.loaded.emojiValueToShortcodes[codepoints],
                        { style: "unit-narrow" }
                    )}">${htmlEscape(codepoints)}</span>`
                )
            )
        );
        node.replaceWith(...span.childNodes);
    }
    return markup(doc.body.innerHTML);
}

/**
 * Converts an object of key/value to string, where object represents a attClass with OWL syntax object
 * and value is evaluation of each key.
 * Example: "attClassObjectToString({ a: 1, b: 0, c: 1 })" converts to "a c".
 */
export function attClassObjectToString(obj) {
    return Object.entries(obj)
        .filter(([_, val]) => val)
        .map(([key, _]) => key)
        .join(" ");
}
