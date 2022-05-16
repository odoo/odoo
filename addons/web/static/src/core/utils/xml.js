/** @odoo-module **/

/**
 * XML document to create new elements from. The fact that this is a "text/xml"
 * document ensures that tagNames and attribute names are case sensitive.
 */
const parser = new DOMParser();
const xmlDocument = parser.parseFromString("<templates/>", "text/xml");

function hasParsingError(parsedDocument) {
    return parsedDocument.getElementsByTagName("parsererror").length > 0;
}

export class XMLParser {
    /**
     * to override. Should return the parsed content of the arch.
     * It can call the visitArch function if desired
     */
    parse() {}

    /**
     * @param {Element | string} xml
     * @param {(el: Element, visitChildren: () => any) => any} callback
     */
    visitXML(xml, callback) {
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
        const xmlDoc = typeof xml === "string" ? this.parseXML(xml) : xml;
        visit(xmlDoc);
    }

    /**
     * @param {string} arch
     * @returns {Element}
     */
    parseXML(arch) {
        const cleanedArch = arch.replace(/&amp;nbsp;/g, "");
        const xml = parser.parseFromString(cleanedArch, "text/xml");
        if (hasParsingError(xml)) {
            throw new Error(
                `An error occured while parsing ${arch}: ${xml.getElementsByTagName("parsererror")}`
            );
        }
        return xml.documentElement;
    }
}

/**
 * @param {string} value
 * @param {boolean} [falsyIfUndefined]
 * @returns {boolean}
 */
export const isFalsy = (value, falsyIfUndefined) =>
    (value ? /^false|0$/i.test(value) : falsyIfUndefined) || false;

/**
 * @param {string} value
 * @param {boolean} [truthyIfUndefined]
 * @returns {boolean}
 */
export const isTruthy = (value, truthyIfUndefined) =>
    (value ? !/^false|0$/i.test(value) : truthyIfUndefined) || false;

/**
 * Combines the existing value of a node attribute with new given parts. The glue
 * is the string used to join the parts.
 *
 * @param {Element} el
 * @param {string} attr
 * @param {string | string[]} parts
 * @param {string} [glue=" "]
 */
export const combineAttributes = (el, attr, parts, glue = " ") => {
    const allValues = [];
    if (el.hasAttribute(attr)) {
        allValues.push(el.getAttribute(attr));
    }
    allValues.push(...(Array.isArray(parts) ? parts : [parts]));
    el.setAttribute(attr, allValues.join(glue));
};

/**
 * XML equivalent of `document.createElement`.
 *
 * @param {string} tagName
 * @param {...(Iterable<Element> | Record<string, string>)} args
 * @returns {Element}
 */
export const createElement = (tagName, ...args) => {
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
};

/**
 * XML equivalent of `document.createTextNode`.
 *
 * @param {string} data
 * @returns {Text}
 */
export const createTextNode = (data) => xmlDocument.createTextNode(data);

/* Transforms a string into a valid expression to be injected
 * in a template as a props via setAttribute.
 * Example: myString = `Some weird language quote (") `;
 *     should become in the template:
 *      <Component label="&quot;Some weird language quote (\\&quot;)&quot; " />
 *     which should be interpreted by owl as a JS expression being a string:
 *      `Some weird language quote (") `
 *
 * @param  {string} str The initial value: a pure string to be interpreted as such
 * @return {string}     the valid string to be injected into a component's node props.
 */
export function transformStringForExpression(str) {
    const delimiter = `"`;
    const newStr = str.replaceAll(delimiter, `\\${delimiter}`);
    return `${delimiter}${newStr}${delimiter}`;
}
