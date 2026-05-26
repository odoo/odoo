import { BasePrinter } from "@point_of_sale/app/utils/printer/base_printer";
import { _t } from "@web/core/l10n/translation";
import { getLNATargetAddressSpace } from "../init_lna";

export class ZebraPrinter extends BasePrinter {
    setup({ printer }) {
        super.setup(...arguments);
        this.printer_ip = printer.printer_ip;
        this.timeout = printer.timeout || 15000;
    }

    get address() {
        return `http://${this.printer_ip}/pstprnt`;
    }

    /**
     * @override
     * Zebra printers host a web server that accepts print jobs
     * This server has not been updated to handle CORS preflight requests,
     * so we have to use "no-cors" mode and can't check the response status.
     */
    async sendPrintingJob(zpl) {
        const params = {
            method: "POST",
            body: zpl,
            signal: AbortSignal.timeout(this.timeout),
            headers: {
                "Content-Length": zpl.length,
                "Content-Type": "text/plain; charset=utf-8",
            },
            mode: "no-cors",
        };

        if (this.use_lna) {
            params.targetAddressSpace = getLNATargetAddressSpace(this.address);
        }

        try {
            await fetch(this.address, params);
            return {
                result: true,
                status: 0,
                canRetry: true,
            };
        } catch {
            return {
                result: false,
                canRetry: true,
            };
        }
    }

    /**
     * @override
     */
    getResultsError(printResult) {
        return {
            successful: false,
            errorCode: "",
            status: status,
            message: {
                title: _t("Printing failed"),
                body: _t("The printer is not reachable."),
            },
            canRetry: printResult.canRetry || false,
        };
    }
}
