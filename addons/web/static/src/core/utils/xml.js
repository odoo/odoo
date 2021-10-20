/** @odoo-module **/

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
     * @param {(node: Element, visitChildren: () => any) => any} callback
     */
    visitXML(xml, callback) {
        const visit = (node) => {
            if (node) {
                let didVisitChildren = false;
                const visitChildren = () => {
                    for (let child of node.children) {
                        visit(child);
                    }
                    didVisitChildren = true;
                };
                const shouldVisitChildren = callback(node, visitChildren);
                if (shouldVisitChildren !== false && !didVisitChildren) {
                    visitChildren();
                }
            }
        };
        const xmlDoc = typeof xml === "string" ? this.parseXML(xml) : xml;
        visit(xmlDoc);
    }

    parseXML(arch) {
        const parser = new DOMParser();
        const xml = parser.parseFromString(arch, "text/xml");
        if (hasParsingError(xml)) {
            throw new Error(
                `An error occured while parsing ${arch}: ${xml.getElementsByTagName("parsererror")}`
            );
        }
        return xml.documentElement;
    }

    isAttr(node, attr) {
        const value = node.getAttribute(attr);
        return {
            truthy: (canBeUndefined) => {
                if (canBeUndefined && !value) {
                    return true;
                }
                return value && /true|1/i.test(value);
            },
            falsy: (canBeUndefined) => {
                if (canBeUndefined && !value) {
                    return true;
                }
                return value && /false|0/i.test(value);
            },
            equalTo: (expected) => value === expected,
            notEqualTo: (expected) => value !== expected,
        };
    }

    getActiveActions(rootNode) {
        return {
            edit: this.isAttr(rootNode, "edit").truthy(true),
            create: this.isAttr(rootNode, "create").truthy(true),
            delete: this.isAttr(rootNode, "delete").truthy(true),
            duplicate: this.isAttr(rootNode, "duplicate").truthy(true),
            export_xlsx: this.isAttr(rootNode, "export_xlsx").truthy(true),
        };
    }
}

/**
 * Combines the existing value of a node attribute with new given parts. The glue
 * is the string used to join the parts.
 * @param {Node} node
 * @param {string} attr
 * @param {string | string[]} parts
 * @param {string} [glue=" "]
 */
export const combineAttributes = (node, attr, parts, glue = " ") => {
    const allValues = [];
    if (node.hasAttribute(attr)) {
        allValues.push(node.getAttribute(attr));
    }
    allValues.push(...(Array.isArray(parts) ? parts : [parts]));
    node.setAttribute(attr, allValues.join(glue));
};
