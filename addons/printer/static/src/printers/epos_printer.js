import { registry } from "@web/core/registry";
import { delay } from "@web/core/utils/concurrency";
import { fetchLocalNetwork, getPrinterUrl, PRINTER_NOT_REACHABLE } from "./local_network";

const TIMEOUT = 15000;
// The printer waits for the previous label to be taken out.
const ERROR_WAIT_EJECT = "ERROR_WAIT_EJECT";
const WAIT_EJECT_RETRY_DELAY = 1000;

/**
 * SOAP envelope printing a raster image then cutting the paper.
 *
 * @param {{ width: number, height: number, raster: string }} image the rows of
 *   the image from the top, 8 dots per byte, a set bit printing black, in base64
 * @returns {string}
 */
export function getEposPrintXml({ width, height, raster }) {
    return (
        `<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">` +
        `<s:Body>` +
        `<epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">` +
        `<image width="${width}" height="${height}" align="center">${raster}</image>` +
        `<cut type="feed" />` +
        `</epos-print>` +
        `</s:Body>` +
        `</s:Envelope>`
    );
}

async function sendEposPrint(printer, xml) {
    let body;
    try {
        const response = await fetchLocalNetwork(
            `${getPrinterUrl(printer)}/cgi-bin/epos/service.cgi?devid=local_printer`,
            // No content type: a "text/plain" request needs no CORS preflight.
            { method: "POST", body: xml, signal: AbortSignal.timeout(TIMEOUT) }
        );
        body = await response.text();
    } catch {
        return { success: false, errorCode: PRINTER_NOT_REACHABLE };
    }
    const document = new DOMParser().parseFromString(body, "application/xml");
    const response = document.querySelector("response");
    if (!response) {
        return { success: false, errorCode: PRINTER_NOT_REACHABLE };
    }
    return {
        success: response.getAttribute("success") === "true",
        errorCode: response.getAttribute("code") || "",
    };
}

/**
 * Epson thermal printers, through their ePOS-Print web service.
 */
export const eposPrinter = {
    /**
     * @param {Object} printer
     * @param {{ width: number, height: number, raster: string }} image
     * @returns {Promise<{ success: boolean, errorCode?: string }>}
     */
    async print(printer, image) {
        const xml = getEposPrintXml(image);
        let result = await sendEposPrint(printer, xml);
        while (result.errorCode === ERROR_WAIT_EJECT) {
            await delay(WAIT_EJECT_RETRY_DELAY);
            result = await sendEposPrint(printer, xml);
        }
        return result;
    },
};

registry.category("printer_drivers").add("epos", eposPrinter);
