import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";
import { Domain } from "@web/core/domain";

/**
 * Support different type of rewards
 *
 * - Free product (product)
 *   Give a free product in exchange of points.
 *
 * - Discount (discount)
 *   Give a discount in exchange of points. The discount can be a fixed
 *   amount or a percentage.
 *
 */
export class LoyaltyReward extends Base {
    static pythonModel = "loyalty.reward";

    get productDiscountSet() {
        return new Set(this.discount_product_ids.map((p) => p.id));
    }

    get discountDomain() {
        return new Domain(this.discount_product_domain);
    }

    getRewards(order, points) {
        const type = this.reward_type;
        if (type === "product" && this.required_points <= points) {
            return {
                type: "product",
                product: this.reward_product_id,
                qty: this.reward_product_qty,
                cost: this.required_points,
                clear: this.clear_wallet,
            };
        }

        if (type === "discount" && this.required_points <= points) {
            const amount = this.getDiscountAmount(order, points);
            if (amount === 0) {
                // This can happen when specifics products aren't matched
                return false;
            }

            return {
                type: "discount",
                discountMode: this.discount_mode,
                discountValue: this.getDiscountAmount(order, points),
                cost: this.required_points,
                clear: this.clear_wallet,
            };
        }

        return false;
    }

    getDiscountAmount(order, points) {
        // Don't care about product, apply on order level
        if (this.discount_applicability === "order") {
            const total = order.displayPrice;
            switch (this.discount_mode) {
                case "percent":
                    return (total * this.discount) / 100;
                case "per_order":
                    return this.discount;
                case "per_point":
                    return this.discount * points;
                default:
                    return 0;
            }
        }

        if (this.discount_applicability === "cheapest") {
            const cheapestLine = order.lines.reduce((cheapest, line) => {
                if (!this.validProducts(line.product_id)) {
                    return cheapest;
                }

                if (!cheapest || line.displayPrice < cheapest.displayPrice) {
                    return line;
                }

                return cheapest;
            }, null);

            if (!cheapestLine) {
                return 0;
            }

            switch (this.discount_mode) {
                case "percent":
                    return (cheapestLine.displayPrice * this.discount) / 100;
                case "per_order":
                    return this.discount;
                case "per_point":
                    return this.discount * points;
                default:
                    return 0;
            }
        }

        if (this.discount_applicability === "specific") {
            const specificLine = order.lines.filter((line) => this.validProducts(line.product_id));
            if (specificLine.length === 0) {
                return 0;
            }

            const amountTotalLines = specificLine.reduce(
                (total, line) => total + line.displayPrice,
                0
            );

            // Assuming we want the first matching line
            switch (this.discount_mode) {
                case "percent":
                    return (amountTotalLines * this.discount) / 100;
                case "per_order":
                    return this.discount;
                case "per_point":
                    return this.discount * points;
                default:
                    return 0;
            }
        }

        return 0;
    }

    validProducts(product) {
        const matchStrictProducts = this.productDiscountSet.has(product.id);
        if (this.productDiscountSet.size > 0 && matchStrictProducts) {
            return true;
        }

        const ruleCateg = this.discount_product_category_id;
        const matchCategory = product.categ_id?.id === ruleCateg?.id;
        if (ruleCateg && matchCategory) {
            return true;
        }

        const emptyDomainValid = !ruleCateg && this.productDiscountSet.size === 0;
        const matchDomainProducts = this.discountDomain.contains(product.raw);
        return (
            (matchDomainProducts && this.discount_product_domain !== "[]") ||
            (emptyDomainValid && this.discount_product_domain === "[]")
        );
    }
}

registry.category("pos_available_models").add(LoyaltyReward.pythonModel, LoyaltyReward);
