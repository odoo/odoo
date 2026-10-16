import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

export class FidelityRule extends Base {
    static pythonModel = "fidelity.rule";

    setup(vals) {
        super.setup(vals);

        this.taxMode = this.program_id.minimum_amount_tax_mode;
        this.possibleProductIdsSet = new Set(this.product_ids.map((p) => p.id));
        this.possibleCategoryIdsSet = new Set(this.product_category_ids.map((c) => c.id));
        this.possibleTagIdsSet = new Set(this.product_tag_ids.map((t) => t.id));
        this.hasProductConditions =
            this.possibleProductIdsSet.size > 0 ||
            this.possibleCategoryIdsSet.size > 0 ||
            this.possibleTagIdsSet.size > 0;
    }

    initState() {
        super.initState();
        this.uiState = {};
    }

    isProductWhitelisted(product) {
        if (!this.hasProductConditions) {
            return true;
        }

        if (this.possibleProductIdsSet.has(product.id)) {
            return true;
        }

        const catMatch = product.categ_id.some((catId) => this.possibleCategoryIdsSet.has(catId));
        const tagMatch = product.tag_ids.some((tagId) => this.possibleTagIdsSet.has(tagId));
        return tagMatch || catMatch;
    }

    redeemablePoints(order) {
        let points = 0;
        let totalEligibleAmount = 0;
        let totalEligibleQuantity = 0;

        for (const line of order.lines) {
            const product = line.getProduct();
            if (!this.isProductWhitelisted(product)) {
                continue;
            }

            totalEligibleAmount += this.taxMode === "incl" ? line.priceIncl : line.priceExcl;
            totalEligibleQuantity += line.qty;
        }

        const neededAmount = this.minimum_amount || 0;
        const neededQuantity = this.minimum_qty || 0;
        const pointsFromAmount = Math.floor(totalEligibleAmount / neededAmount) || 0;
        const pointsFromQuantity = Math.floor(totalEligibleQuantity / neededQuantity) || 0;

        if (neededAmount > 0 && neededQuantity > 0) {
            points = Math.min(pointsFromAmount, pointsFromQuantity);
        } else {
            points = pointsFromAmount || pointsFromQuantity;
        }

        switch (this.reward_point_mode) {
            case "order":
                return points * this.reward_point_amount;
            case "money":
                return pointsFromAmount * this.reward_point_amount;
            case "unit":
                return pointsFromQuantity * this.reward_point_amount;
        }

        return 0;
    }
}

registry.category("pos_available_models").add(FidelityRule.pythonModel, FidelityRule);
