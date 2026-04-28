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

        for (const coupon of points) {
            for (const label of ["Won", "Spent", "Balance"]) {
                const key = label.toLowerCase();
                if (coupon.points[key]) {
                    data.extra_data.loyalties.push({
                        name: coupon.program.portal_point_name,
                        type: _t(label + ":"),
                        points: coupon.points[key],
                    });
                }
            }
        }

        data.extra_data.new_coupons = (this.order.new_coupon_info || []).map((coupon) => ({
            name: coupon.program_name,
            code: coupon.code,
            expiration_date: coupon.expiration_date,
            barcode_base64: coupon.barcode_base64,
        }));

        return data;
    },
});
