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

    visitXML(xml, callback) {
        function visit(xml) {
            if (xml) {
                let didVisitChildren = false;
                const visitChildren = () => {
                    for (let child of xml.children) {
                        visit(child);
                    }
                    didVisitChildren = true;
                };
                const shouldVisitChildren = callback(xml, visitChildren);
                if (shouldVisitChildren !== false && !didVisitChildren) {
                    visitChildren();
                }
            }
        }
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
