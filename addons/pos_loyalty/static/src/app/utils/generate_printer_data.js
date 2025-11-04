import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/generate_printer_data";
import { _t } from "@web/core/l10n/translation";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateData() {
        const data = super.generateData(...arguments);
        const points = this.order.getLoyaltyPoints();
        data.extra_data.loyalties = [];

        for (const coupon of points) {
            data.extra_data.loyalties.push({
                name: coupon.program.name,
                type: coupon.points.won >= 0 ? _t("Won:") : _t("Spent:"),
                points: coupon.points.won || coupon.points.spent,
            });
            data.extra_data.loyalties.push({
                name: coupon.program.name,
                type: _t("Balance:"),
                points: coupon.points.balance,
            });
        }

        if (this.order.new_coupon_info) {
            for (const coupon of this.order.new_coupon_info) {
                data.extra_data.loyalties.push({
                    name: coupon.program_name,
                    type: "",
                    points: coupon.code,
                    barcode_base64: coupon.barcode_base64,
                });
            }
        }

        return data;
    },
});
