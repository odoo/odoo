import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";
import { _t } from "@web/core/l10n/translation";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        data.conditions.from_self = ["mobile", "kiosk"].includes(this.order.source);
        return data;
    },
    generatePreparationData(categoryIdsSet, opts = { orderChange: null }) {
        const receipts = super.generatePreparationData(...arguments);
        for (const receipt of receipts) {
            if ("mobile" === this.order.source) {
                receipt.extra_data.prefix = _t("Self Order");
            } else if ("kiosk" === this.order.source) {
                receipt.extra_data.prefix = _t("Kiosk Order");
            } else {
                continue;
            }

            if (receipt.order.table_stand_number) {
                receipt.extra_data.order_label = _t(
                    "Table Tracker %s",
                    receipt.order.table_stand_number
                );
            } else if (!receipt.order.table_id) {
                receipt.extra_data.order_label = false;
            }
        }
        return receipts;
    },
    generateDynamicQrData({ qrCode }) {
        return {
            company: this.company.raw,
            config: this.config.raw,
            order: this.order.raw,
            image: {
                logo: this.config.receiptLogoUrl,
            },
            qrCode,
            extra_data: {
                ...this.commonExtraData,
                cashier_name: this.order.getCashierName(),
                formated_date_order: this.order.formatDateOrTime("date_order", "datetime"),
                table_name: this.order.table_id?.getName(),
            },
        };
    },
});
