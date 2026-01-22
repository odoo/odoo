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

    sync_from_ui(data) {
        for (const order of data) {
            for (const sell_loyalty_card of order["loyalty_card_ids"]) {
                sell_loyalty_card[2]["code"] =
                    sell_loyalty_card[2]["code"] || this.env["loyalty.card"]._generate_code();
            }
        }
        const records = super.sync_from_ui(data);

        const rewardLines = records["pos.order.line"].filter((line) => line.is_reward_line);
        for (const line of rewardLines) {
            const coupon = this.env["loyalty.card"].browse(line.coupon_id);
            if (coupon) {
                this.env["loyalty.card"].write([coupon[0]["id"]], {
                    points: coupon[0]["points"] - line.points_cost,
                });
            }
        }
        const couponIds = new Set();
        const config_id = records["pos.order"][0]?.config_id;
        for (const order of this.env["pos.order"].browse(records["pos.order"].map((o) => o.id))) {
            for (const line of this.env["pos.order.line"].browse(order["lines"])) {
                if (line.is_reward_line && line.coupon_id) {
                    couponIds.add(line.coupon_id);
                }
            }
            for (const couponId of order["loyalty_card_ids"]) {
                couponIds.add(couponId);
            }
        }
        const coupons = this.env["loyalty.card"].read(
            couponIds,
            this.env["loyalty.card"]._load_pos_data_fields(config_id),
            false
        );
        const programIds = new Set(coupons.map((c) => c.program_id));
        const programs = this.env["loyalty.program"].read(
            programIds,
            this.env["loyalty.program"]._load_pos_data_fields(config_id),
            false
        );

        records["loyalty.card"] = coupons;
        records["loyalty.program"] = programs;
        return records;
    },
});
