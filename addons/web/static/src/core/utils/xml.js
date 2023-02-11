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
