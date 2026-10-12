import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/../tests/unit/data/pos_order.data";
import { _t } from "@web/core/l10n/translation";

patch(PosOrder.prototype, {
    validate_coupon_programs(self, point_changes) {
        const couponIdsFromPos = new Set(Object.keys(point_changes).map((id) => parseInt(id)));

        const coupons = this.env["loyalty.card"]
            .browse([...couponIdsFromPos])
            .filter((c) => c && c.program_id);

        const couponDifference = new Set(
            [...couponIdsFromPos].filter((id) => !coupons.find((c) => c.id === id))
        );

        if (couponDifference.size > 0) {
            return {
                successful: false,
                payload: {
                    message: _t(
                        "Some coupons are invalid. The applied coupons have been updated. Please check the order."
                    ),
                    removed_coupons: [...couponDifference],
                },
            };
        }

        for (const coupon of coupons) {
            const needed = -point_changes[coupon.id];
            if (parseFloat(coupon.points.toFixed(2)) < parseFloat(needed.toFixed(2))) {
                return {
                    successful: false,
                    payload: {
                        message: _t("There are not enough points for the coupon: %s.", coupon.code),
                        updated_points: Object.fromEntries(coupons.map((c) => [c.id, c.points])),
                    },
                };
            }
        }

        return {
            successful: true,
            payload: {},
        };
    },

    confirm_coupon_programs(self, coupon_data) {
        const couponNewIdMap = {};
        for (const k of Object.keys(coupon_data)) {
            const id = parseInt(k);
            if (id > 0) {
                couponNewIdMap[id] = id;
            }
        }

        const couponsToCreate = Object.fromEntries(
            Object.entries(coupon_data).filter(([k]) => parseInt(k) < 0)
        );

        const couponCreateVals = Object.values(couponsToCreate).map((p) => ({
            program_id: p.program_id,
            partner_id: p.partner_id || false,
            code: p.code || p.barcode || `CODE${Math.floor(Math.random() * 10000)}`,
            points: p.points || 0,
        }));

        const newCouponIds = this.env["loyalty.card"].create(couponCreateVals);
        const newCoupons = this.env["loyalty.card"].browse(newCouponIds);

        for (let i = 0; i < Object.keys(couponsToCreate).length; i++) {
            const oldId = parseInt(Object.keys(couponsToCreate)[i], 10);
            const newCoupon = newCouponIds[i];
            couponNewIdMap[oldId] = newCoupon.id;
        }

        const allCoupons = this.env["loyalty.card"].browse(Object.keys(couponNewIdMap).map(Number));
        for (const coupon of allCoupons) {
            const oldId = couponNewIdMap[coupon.id];
            if (oldId && coupon_data[oldId]) {
                coupon.points += coupon_data[oldId].points;
            }
        }

        return {
            coupon_updates: allCoupons.map((coupon) => ({
                old_id: couponNewIdMap[coupon.id],
                id: coupon.id,
                points: coupon.points,
                code: coupon.code,
                program_id: coupon.program_id,
                partner_id: coupon.partner_id,
            })),
            program_updates: [...new Set(allCoupons.map((c) => c.program_id))].map((program) => ({
                program_id: program,
                usages: this.env["loyalty.program"].browse(program)?.[0]?.total_order_count,
            })),
            new_coupon_info: newCoupons.map((c) => ({
                program_name: this.env["loyalty.program"].browse(c.program_id)?.[0]?.name || "",
                expiration_date: c.expiration_date || false,
                code: c.code,
            })),
            coupon_report: {},
        };
    },

    add_loyalty_history_lines() {
        return true;
    },
});
