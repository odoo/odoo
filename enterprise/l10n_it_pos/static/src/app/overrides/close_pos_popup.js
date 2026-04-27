/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { isFiscalPrinterActive } from "./helpers/utils";

patch(ClosePosPopup.prototype, {
    downloadSalesReport() {
        if (!isFiscalPrinterActive(this.pos.config)) {
            return super.downloadSalesReport();
        } else {
            return this.pos.fiscalPrinter.printXReport();
        }
    },
    async closeSession() {
        if (isFiscalPrinterActive(this.pos.config)) {
            const zResult = await this.pos.fiscalPrinter.printZReport();
            if (!zResult.success) {
                // print XZ report if the Z report failed because of status 17.
                // It means we are in a test environment.
                // Fallback to print XZ report.
                if (zResult.status === "17") {
                    const xzResult = await this.pos.fiscalPrinter.printXZReport();
                    if (!xzResult.success) {
                        return;
                    }
                }
            }
        }
        return super.closeSession();
    },
});
