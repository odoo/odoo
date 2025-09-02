import { parseXML } from "@web/core/utils/xml";
import { GLORY_RESULT } from "./constants";

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

/**
 * Takes an XML response and returns a status
 * string e.g. "SUCCESS" or "CHANGE_SHORTAGE"
 *
 * @param {Element} xmlResponse
 * @returns {string}
 */
export function parseGloryResult(xmlResponse) {
    const resultString = GLORY_RESULT[xmlResponse.getAttribute("result")];
    if (!resultString) {
        throw new Error("Not a valid Glory XML response");
    }

    return resultString;
}

/**
 * Takes an XML response containing the verification status
 * of the Glory machine, and returns a number from 0-3
 * corresponding to the required verification action:
 *
 *   `0`: No verification needed
 *
 *   `1`: Notes and coins need verification
 *
 *   `2`: Notes need verification
 *
 *   `3`: Coins need verification
 *
 * This result can be passed directly into a `CollectRequest`
 * to trigger the verification process.
 *
 * @param {Element} xmlResponse
 * @returns {0 | 1 | 2 | 3}
 */
export function parseVerificationInfo(xmlResponse) {
    const denominationInfos = Array.from(
        xmlResponse.getElementsByTagName("RequireVerifyDenomination")
    );
    const collectionContainerInfos = Array.from(
        xmlResponse.getElementsByTagName("RequireVerifyCollectionContainer")
    );
    const mixStackerInfos = Array.from(xmlResponse.getElementsByTagName("RequireVerifyMixStacker"));
    const allInfos = [...denominationInfos, ...collectionContainerInfos, ...mixStackerInfos];

    const notesRequireVerify = allInfos.some(
        (info) => info.getAttribute("devid") === "1" && info.getAttribute("val") === "1"
    );
    const coinsRequireVerify = allInfos.some(
        (info) => info.getAttribute("devid") === "2" && info.getAttribute("val") === "1"
    );

    if (notesRequireVerify && coinsRequireVerify) {
        return 1;
    }
    if (notesRequireVerify) {
        return 2;
    }
    if (coinsRequireVerify) {
        return 3;
    }

    return 0;
}
