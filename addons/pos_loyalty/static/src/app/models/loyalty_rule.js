import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";
import { Domain } from "@web/core/domain";

export class LoyaltyRule extends Base {
    static pythonModel = "loyalty.rule";

    get productSet() {
        return new Set(this.product_ids.map((p) => p.id));
    }

    get domain() {
        return new Domain(this.product_domain);
    }

    getPoints(order) {
        if (!this.checkRule(order)) {
            return 0;
        }

        const amontByMatch = parseInt(this.reward_point_amount) || 0;
        const { totalQty, totalPrice } = this.getOrderTotalQtyAndPrice(order);
        switch (this.reward_point_mode) {
            case "order":
                return 1 * amontByMatch;
            case "unit":
                return totalQty * amontByMatch;
            case "money":
                return Math.floor(totalPrice) * amontByMatch;
            default:
                return 0;
        }
    }

    checkRule(order) {
        const minimumQty = this.minimum_qty || 0;
        const minimumAmount = this.minimum_amount || 0;
        const { totalQty, totalPrice } = this.getOrderTotalQtyAndPrice(order);
        return totalQty >= minimumQty && totalPrice >= minimumAmount;
    }

    getOrderTotalQtyAndPrice(order) {
        const taxMode = this.minimum_amount_tax_mode;
        const usableLines = order.lines.filter((line) => this.validProducts(line.product_id));
        return usableLines.reduce(
            (acc, line) => {
                acc.totalQty += line.qty;

                if (taxMode === "excl") {
                    acc.totalPrice += line.priceExcl;
                } else {
                    acc.totalPrice += line.priceIncl;
                }

                return acc;
            },
            { totalQty: 0, totalPrice: 0 }
        );
    }

    validProducts(product) {
        const matchStrictProducts = this.productSet.has(product.id);
        if (this.productSet.size > 0 && matchStrictProducts) {
            return true;
        }

        const ruleCateg = this.product_category_id;
        const matchCategory = product.categ_id?.id === ruleCateg?.id;
        if (ruleCateg && matchCategory) {
            return true;
        }

        const emptyDomainValid = !ruleCateg && this.productSet.size === 0;
        const matchDomainProducts = this.domain.contains(product.raw);
        return (
            (matchDomainProducts && this.product_domain !== "[]") ||
            (emptyDomainValid && this.product_domain === "[]")
        );
    }
}

registry.category("pos_available_models").add(LoyaltyRule.pythonModel, LoyaltyRule);
