import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";
import { Domain } from "@web/core/domain";

export class LoyaltyReward extends Base {
    static pythonModel = "loyalty.reward";

    /**
     * Builds the reward line values for applying this reward on the given order.
     * - free product: one line at price 0 for the free product, with the maximum qty affordable
     *   with the given points
     * - discount: the discountable lines are split into separate tax groups and a negative line is
     *   produced per tax group, weighted by each group's contribution to the discountable total
     * mirror of *models/loyalty_reward.py* LoyaltyReward._get_pos_points_cost
     * @param {object} order
     * @param {number} points - the points available to spend on the reward
     * @param {object} opts - additional parameters. Here used to indicate for multi_product rewards
     *  which product use
     * @returns {object[]} the reward line value objects
     */
    getRewardLines(order, points, opts) {
        const mapTaxes = (taxes) =>
            order.fiscal_position_id
                ? order.fiscal_position_id.getTaxesAfterFiscalPosition(taxes)
                : taxes;

        const linkTaxes = (taxes) => taxes.map((tax) => ["link", tax]);

        if (this.reward_type === "product") {
            let product = this.reward_product_id || this.reward_product_ids[0];
            if (this.multi_product) {
                product = opts.reward_product_id;
            }
            if (!product) {
                return [];
            }

            const claimableCount = this.clear_wallet
                ? 1
                : Math.floor(points / this.required_points);

            if (claimableCount <= 0) {
                return [];
            }

            const maxQty = this.reward_product_qty * claimableCount;
            const qty = opts?.qty ? Math.min(opts.qty, maxQty) : maxQty;

            const pointsCost = this.clear_wallet
                ? points
                : Math.ceil(qty / this.reward_product_qty) * this.required_points;

            return [
                {
                    product_id: product,
                    qty: qty,
                    price_unit: 0,
                    price_type: "manual",
                    tax_ids: linkTaxes(mapTaxes(product.taxes_id)),
                    attribute_value_ids:
                        opts?.attribute_value_ids.map((attr) => ["link", attr]) || [],
                    custom_attribute_value_ids: Object.entries(
                        opts?.attribute_custom_values || {}
                    ).reduce((acc, [id, cus]) => {
                        if (cus === null || cus === undefined) {
                            return acc;
                        }
                        acc.push([
                            "create",
                            {
                                custom_product_template_attribute_value_id:
                                    this.models["product.template.attribute.value"].get(id),
                                custom_value: cus,
                            },
                        ]);
                        return acc;
                    }, []),
                    is_reward_line: true,
                    reward_id: this,
                    points_cost: pointsCost,
                },
            ];
        }

        // reward_type === "discount"
        const lines = this.getDiscountApplicableLines(order);
        if (!lines.length) {
            return [];
        }

        const pricedLines = lines.flatMap((line) =>
            line.combo_line_ids.length
                ? line.getAllLinesInCombo().filter((l) => !l.combo_line_ids.length)
                : [line]
        );

        const perUnit = this.discount_applicability === "cheapest";
        const discountableOf = (line) => {
            const price = order.getLineDiscountablePrice(line.uuid);
            const qty = line.getQuantity();
            return perUnit && qty ? price / qty : price;
        };
        const discountable = pricedLines.reduce((total, line) => total + discountableOf(line), 0);
        if (!discountable) {
            return [];
        }

        let maxDiscount = Math.min(order.priceIncl, this.discount_max_amount || order.priceIncl);
        let pointsCost = this.clear_wallet ? points : this.required_points;
        if (this.discount_mode === "per_point") {
            if (this.clear_wallet) {
                maxDiscount = Math.min(maxDiscount, this.discount * this.required_points);
            } else {
                const affordablePoints =
                    Math.floor(points / this.required_points) * this.required_points;
                maxDiscount = Math.min(maxDiscount, this.discount * affordablePoints);
                pointsCost = this.currency_id.round(
                    Math.min(maxDiscount, discountable) / this.discount
                );
            }
        } else if (this.discount_mode === "per_order") {
            maxDiscount = Math.min(maxDiscount, this.discount);
        } else if (this.discount_mode === "percent") {
            maxDiscount = Math.min(maxDiscount, discountable * (this.discount / 100));
        }

        const factor = Math.min(1, maxDiscount / discountable);
        const groups = {};
        for (const pricedLine of pricedLines) {
            const discountablePrice = discountableOf(pricedLine);

            const netRatio = pricedLine.priceIncl ? discountablePrice / pricedLine.priceIncl : 1;
            const taxes = mapTaxes(pricedLine.tax_ids).filter((tax) => tax.amount_type !== "fixed");
            const key = taxes
                .map((tax) => tax.id)
                .sort()
                .join("-");
            if (!groups[key]) {
                groups[key] = { taxes, included: 0, excluded: 0 };
            }
            groups[key].included += pricedLine.priceIncl * netRatio;
            groups[key].excluded += pricedLine.priceExcl * netRatio;

            order._line_discountable_price[pricedLine.uuid] =
                order.getLineDiscountablePrice(pricedLine.uuid) - discountablePrice * factor;
        }
        return Object.values(groups)
            .filter((group) => group.included)
            .map((group, index) => {
                const priceIncluded = group.taxes.some((tax) => tax.price_include);
                const base = priceIncluded ? group.included : group.excluded;
                return {
                    product_id: this.discount_line_product_id,
                    qty: 1,
                    price_unit: -(base * factor),
                    price_type: "manual",
                    tax_ids: linkTaxes(group.taxes),
                    is_reward_line: true,
                    reward_id: this,
                    points_cost: index === 0 ? pointsCost : 0,
                };
            });
    }

    /**
     * Gets the lines of ``order`` for which this (discount) reward is applicable.
     * @param {object} order
     * @returns {PosOrderline[]} the lines for which the discount can be applied
     */
    getDiscountApplicableLines(order) {
        if (this.reward_type !== "discount") {
            return [];
        }
        const candidateLines = order
            .getOrderlines()
            .filter(
                (line) =>
                    !line.is_reward_line &&
                    !line.combo_parent_id &&
                    !line.isTipLine() &&
                    line.getQuantity() > 0 &&
                    line.linePriceTaxIncluded > 0 &&
                    !line.isServiceFeeLine()
            );
        if (this.discount_applicability === "cheapest") {
            const productIds = this.getDiscountProductIds();
            const eligibleLines = productIds
                ? candidateLines.filter((line) => productIds.has(line.getProduct().id))
                : candidateLines;
            let cheapest = null;
            let cheapestUnitPrice = null;
            for (const line of eligibleLines) {
                const unitPrice = line.linePriceTaxIncluded / line.getQuantity();
                if (cheapest === null || unitPrice < cheapestUnitPrice) {
                    cheapest = line;
                    cheapestUnitPrice = unitPrice;
                }
            }
            return cheapest ? [cheapest] : [];
        }
        if (this.discount_applicability === "specific") {
            const productIds = this.getDiscountProductIds();
            return candidateLines.filter(
                (line) => !productIds || productIds.has(line.getProduct().id)
            );
        }

        // discount_applicability === "order"
        return candidateLines;
    }

    /**
     * Resolves the set of product ids this discount reward applies to.
     * When `loyalty.compute_all_discount_product_ids` is enabled the server ships the
     * list in `all_discount_product_ids`. When it is disabled the server ships the domain
     * `reward_product_domain` instead, to be evaluated client-side against loaded products.
     * @returns {Set<number>|null} the applicable product ids, or null when unrestricted
     * @throws {InvalidDomainError|TypeError} when the domain can't be evaluated client-side
     */
    getDiscountProductIds() {
        if (this.all_discount_product_ids.length) {
            return new Set(this.all_discount_product_ids.map((product) => product.id));
        }
        const domainStr = this.reward_product_domain;
        if (!domainStr || domainStr === "null") {
            return null;
        }
        const domainList = JSON.parse(domainStr);
        if (!domainList.length) {
            return null;
        }
        const domain = new Domain(domainList);
        return new Set(
            this.models["product.product"]
                .filter((product) => domain.contains(product.raw))
                .map((product) => product.id)
        );
    }
}

registry.category("pos_available_models").add(LoyaltyReward.pythonModel, LoyaltyReward);
