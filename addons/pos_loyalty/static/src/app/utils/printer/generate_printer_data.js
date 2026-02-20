import { patch } from "@web/core/utils/patch";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";
import { _t } from "@web/core/l10n/translation";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
        const points = this.order.getLoyaltyPoints();
        data.extra_data.loyalties = [];

        const capitalizeFirst = (s) => s && s[0].toUpperCase() + s.slice(1);

        for (const coupon of points) {
            for (const key of ["won", "spent", "balance"]) {
                if (coupon.points[key]) {
                    data.extra_data.loyalties.push({
                        name: coupon.program.portal_point_name,
                        type: _t(capitalizeFirst(key) + ":"),
                        points: coupon.points[key],
                    });
                }
            }
        }

        data.extra_data.new_coupons = (this.order.new_coupon_info || []).map((coupon) => ({
            name: coupon.program_name,
            code: coupon.code,
            barcode_base64: coupon.barcode_base64,
        }));

        return data;
    },
});
