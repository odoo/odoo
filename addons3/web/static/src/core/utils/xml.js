/** @odoo-module **/

/**
 * XML document to create new elements from. The fact that this is a "text/xml"
 * document ensures that tagNames and attribute names are case sensitive.
 */
const serializer = new XMLSerializer();
const parser = new DOMParser();
const xmlDocument = parser.parseFromString("<templates/>", "text/xml");

function hasParsingError(parsedDocument) {
    return parsedDocument.getElementsByTagName("parsererror").length > 0;
}

/**
 * @param {string} str
 * @returns {Element}
 */
export function parseXML(str) {
    const xml = parser.parseFromString(str, "text/xml");
    if (hasParsingError(xml)) {
        throw new Error(
            `An error occured while parsing ${str}: ${xml.getElementsByTagName("parsererror")}`
        );
    }
    return xml.documentElement;
}

/**
 * @param {Element} xml
 * @returns {string}
 */
export function serializeXML(xml) {
    return serializer.serializeToString(xml);
}

/**
 * @param {Element | string} xml
 * @param {(el: Element, visitChildren: () => any) => any} callback
 */
export function visitXML(xml, callback) {
    const visit = (el) => {
        if (el) {
            let didVisitChildren = false;
            const visitChildren = () => {
                for (const child of el.children) {
                    visit(child);
                }
                didVisitChildren = true;
            };
            const shouldVisitChildren = callback(el, visitChildren);
            if (shouldVisitChildren !== false && !didVisitChildren) {
                visitChildren();
            }
        }
    };
    const xmlDoc = typeof xml === "string" ? parseXML(xml) : xml;
    visit(xmlDoc);
}

/**
 * @param {Element} parent
 * @param {Node | Node[] | void} node
 */
export function append(parent, node) {
    const nodes = Array.isArray(node) ? node : [node];
    parent.append(...nodes.filter(Boolean));
    return parent;
}

/**
 * Combines the existing value of a node attribute with new given parts. The glue
 * is the string used to join the parts.
 *
 * @param {Element} el
 * @param {string} attr
 * @param {string | string[]} parts
 * @param {string} [glue=" "]
 */
export function combineAttributes(el, attr, parts, glue = " ") {
    const allValues = [];
    if (el.hasAttribute(attr)) {
        allValues.push(el.getAttribute(attr));
    }
    parts = Array.isArray(parts) ? parts : [parts];
    parts = parts.filter((part) => !!part);
    allValues.push(...parts);
    el.setAttribute(attr, allValues.join(glue));
}

/**
 * XML equivalent of `document.createElement`.
 *
 * @param {string} tagName
 * @param {...(Iterable<Element> | Record<string, string>)} args
 * @returns {Element}
 */
export function createElement(tagName, ...args) {
    const el = xmlDocument.createElement(tagName);
    for (const arg of args) {
        if (!arg) {
            continue;
        }
        if (Symbol.iterator in arg) {
            // Children list
            el.append(...arg);
        } else if (typeof arg === "object") {
            // Attributes
            for (const name in arg) {
                el.setAttribute(name, arg[name]);
            }
        }
    }
    return el;
}

/**
 * XML equivalent of `document.createTextNode`.
 *
 * @param {string} data
 * @returns {Text}
 */
export function createTextNode(data) {
    return xmlDocument.createTextNode(data);
}

/**
 * Removes the given attributes on the given element and returns them as a dictionnary.
 * @param {Element} el
 * @param {string[]} attributes
 * @returns {Record<string, string>}
 */
export function extractAttributes(el, attributes) {
    const attrs = Object.create(null);
    for (const attr of attributes) {
        attrs[attr] = el.getAttribute(attr) || "";
        el.removeAttribute(attr);
    }
    return attrs;
}

/**
 * @param {Node} [node]
 * @param {boolean} [lower=false]
 * @returns {string}
 */
export function getTag(node, lower = false) {
    const tag = (node && node.nodeName) || "";
    return lower ? tag.toLowerCase() : tag;
}

/**
 * @param {Node} node
 * @param {Object} attributes
 */
export function setAttributes(node, attributes) {
    for (const [name, value] of Object.entries(attributes)) {
        node.setAttribute(name, value);
    }
}
