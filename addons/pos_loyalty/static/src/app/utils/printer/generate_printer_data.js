import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { roundPrecision } from "@web/core/utils/numbers";

patch(GeneratePrinterData.prototype, {
    generateReceiptData() {
        const data = super.generateReceiptData(...arguments);
<<<<<<< b9823b8a6ed7f33c4450ac6dbe2dabed3ca6a6e7
        data.extra_data.loyalties = this._generateLoyaltyReceiptData();
        data.extra_data.new_coupons = this._generateNewCouponsReceiptData();
||||||| ba2d10f169b8c26d04c5b9fdd491673dc0005768
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

=======
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
        if (!data.extra_data.loyalties.length && this.order.raw.loyalties) {
            data.extra_data.loyalties = this.order.raw.loyalties;
        }

        data.extra_data.new_coupons = (
            this.order.new_coupon_info ||
            this.order.raw.new_coupon_info ||
            []
        ).map((coupon) => ({
            program_name: coupon.program_name,
            code: coupon.code,
            expiration_date: coupon.expiration_date,
            barcode_base64: coupon.barcode_base64,
        }));

>>>>>>> 1d4b494756ee63a4a1d786ff0c78cb9c618aa0af
        return data;
    },
    /**
     * Coupons this order issued for a future order, printed with their barcode so the
     * customer can redeem them next time.
     * @returns {object[]}
     */
    _generateNewCouponsReceiptData() {
        const order = this.order;
        return this.models["loyalty.card"]
            .filter(
                (card) =>
                    card.source_pos_order_id?.id === order.id &&
                    card.program_id?.applies_on === "future" &&
                    !["gift_card", "ewallet"].includes(card.program_id?.program_type) &&
                    card._barcode_base64
            )
            .map((card) => ({
                name: card.program_id.name,
                code: card.code,
                expiration_date: card.expiration_date,
                barcode_base64: card._barcode_base64,
            }));
    },
    /**
     * Points summary printed on the receipt for each loyalty program that took part in the
     * order: points won and spent by this order, and the card's resulting balance.
     * @returns {object[]}
     */
    _generateLoyaltyReceiptData() {
        const order = this.order;
        const loyalties = [];
        for (const program of this.models["loyalty.program"].filter(
            (program) => program.program_type === "loyalty"
        )) {
            const won = program.getEarnedPoints(order);
            const spent = program.getSpentPoints(order);
            // Only programs this order actually touched get a line.
            if (won <= 0 && spent <= 0) {
                continue;
            }
            const name = program.portal_point_name;
            const round = (points) => roundPrecision(points, 0.01);
            if (won > 0) {
                loyalties.push({ name, type: _t("Won:"), points: round(won) });
            }
            if (spent > 0) {
                loyalties.push({ name, type: _t("Spent:"), points: round(spent) });
            }
            loyalties.push({
                name,
                type: _t("Balance:"),
                points: round(
                    order.isSynced
                        ? program.getAvailablePoints(order)
                        : program.getNewBalance(order)
                ),
            });
        }
        return loyalties;
    },
});
