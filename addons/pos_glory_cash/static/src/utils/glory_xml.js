import { parseXML } from "@web/core/utils/xml";

/**
 * @param {Blob} xmlBlob
 */
export async function parseGloryXml(xmlBlob) {
    const text = await xmlBlob.text();
    // Remove control characters from Glory response string
    const xmlString = text.replace(/[\cD\0]/g, "");
    return parseXML(xmlString);
}

/**
 * @param {import("models").GloryXmlElement} gloryElement
 */
function gloryElementToDomElement(gloryElement) {
    if (typeof gloryElement === "string") {
        return document.createTextNode(gloryElement);
    }
    const element = document.createElementNS(null, gloryElement.name);
    for (const [key, value] of Object.entries(gloryElement.attributes ?? {})) {
        element.setAttribute(key, value);
    }
    for (const child of gloryElement.children ?? []) {
        element.appendChild(gloryElementToDomElement(child));
    }
    return element;
}

/**
 * @param {import("models").GloryXmlElement} gloryElement
 */
export function serializeGloryXml(gloryElement) {
    const domElement = gloryElementToDomElement(gloryElement);
    const xmlString = new XMLSerializer().serializeToString(domElement);
    return xmlString + "\0";
}

/**
 * @param {number} sequenceNumber
 * @param {string} sessionId
 * @returns {import("models").GloryXmlElement[]}
 */
export const makeGloryHeader = (sequenceNumber, sessionId) => {
    const sequenceNumberString = sequenceNumber.toString(10).padStart(11, "0");
    return [
        {
            name: "Id",
            children: ["OdooPos"],
        },
        {
            name: "SeqNo",
            children: [sequenceNumberString],
        },
        {
            name: "SessionID",
            children: [sessionId],
        },
    ];
};
