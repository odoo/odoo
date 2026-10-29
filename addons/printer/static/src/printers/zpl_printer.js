import { registry } from "@web/core/registry";
import { fetchLocalNetwork, getPrinterUrl, PRINTER_NOT_REACHABLE } from "./local_network";

/**
 * Zebra label printers: they print the ZPL code POSTed to their web server.
 *
 * Their web server does not answer CORS preflight requests, so the request is
 * sent in "no-cors" mode and its response cannot be read: a request that went
 * through counts as printed.
 */
export const zplPrinter = {
    /**
     * @param {Object} printer
     * @param {string} zpl
     * @returns {Promise<{ success: boolean, errorCode?: string }>}
     */
    async print(printer, zpl) {
        try {
            await fetchLocalNetwork(`${getPrinterUrl(printer)}/pstprnt`, {
                method: "POST",
                body: zpl,
                headers: { "Content-Type": "text/plain; charset=utf-8" },
                mode: "no-cors",
            });
        } catch {
            return { success: false, errorCode: PRINTER_NOT_REACHABLE };
        }
        return { success: true };
    },
};

registry.category("printer_drivers").add("zpl", zplPrinter);
