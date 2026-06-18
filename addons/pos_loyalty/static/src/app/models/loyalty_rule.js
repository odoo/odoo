import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";
import { roundPrecision } from "@web/core/utils/numbers";

export class LoyaltyRule extends Base {
    static pythonModel = "loyalty.rule";

    /**
     * Whether the line's product falls within this rule's product domain.
     * mirror of *models/loyalty_rule.py* LoyaltyRule._in_domain
     * @param {object} line
     * @returns {boolean}
     */
    _inDomain(line) {
        return (
            this.any_product ||
            this.valid_product_ids.some((product) => product.id === line.getProduct().id)
        );
    }

    /**
     * Whether `code` activates this rule: a with_code rule matches either its typed
     * code or its generated promo barcode.
     * @param {string} code
     * @returns {boolean}
     */
    matchCode(code) {
        return this.mode === "with_code" && (this.code === code || this.promo_barcode === code);
    }

    /**
     * Whether a line participates in this rule's point computations at all. Combo children
     * (priced through their parent) and tips never earn points.
     * mirror of *models/loyalty_rule.py* LoyaltyRule._counts_for_points
     * @param {object} line
     * @returns {boolean}
     */
    _countsForPoints(line) {
        return !line.combo_parent_id && !line.isTipLine();
    }

    /**
     * Lines that match this rule's product domain (the goods it applies to).
     * Payment-program topup lines never earn points — the backend achieves the same by
     * scoring only the non-topup lines in _process_loyalty.
     * mirror of *models/loyalty_rule.py* LoyaltyRule._qualifying_lines
     * @param {object} order
     * @returns {object[]} the order lines eligible for this rule
     */
    _qualifyingLines(order) {
        return order
            .getOrderlines()
            .filter(
                (line) =>
                    !line.is_reward_line &&
                    !line.payment_program_id &&
                    this._countsForPoints(line) &&
                    this._inDomain(line)
            );
    }

    /**
     * Whether the order satisfies this rule's conditions (code activated, eligible
     * products, minimum quantity and amount)
     * mirror of *models/loyalty_rule.py* LoyaltyRule._is_fulfilled
     * @param {object} order
     * @returns {boolean}
     */
    isFulfilled(order) {
        if (this.mode === "with_code" && !order.applied_codes.includes(this.code)) {
            return false;
        }
        const qualifyingLines = this._qualifyingLines(order);
        if (!qualifyingLines.length) {
            return false;
        }
        const totalQty = qualifyingLines.reduce((qty, line) => qty + line.getQuantity(), 0);
        if (totalQty < this.minimum_qty) {
            return false;
        }
        const amount = qualifyingLines.reduce(
            (total, line) =>
                total +
                (this.minimum_amount_tax_mode === "incl"
                    ? line.linePriceTaxIncluded
                    : line.linePriceTaxExcluded),
            0
        );
        return amount >= this.minimum_amount;
    }

    /**
     * Points this rule generates for the given order.
     * mirror of *models/loyalty_rule.py* LoyaltyRule._get_pos_order_points
     * @param {object} order
     * @returns {number} the number of points
     */
    getPoints(order) {
        if (!this.reward_point_amount || !this.isFulfilled(order)) {
            return 0;
        }
        const qualifyingLines = this._qualifyingLines(order);
        switch (this.reward_point_mode) {
            case "order":
                return this.reward_point_amount;
            case "money": {
                // Points are earned on the net amount actually paid, so a discount granted
                // by another program reduces them (mirrors sale_loyalty). A program never
                // counts its own rewards (it shouldn't cannibalise its own points), nor gift
                // card / eWallet payment lines (those aren't discounts on the goods).
                const isExcludedReward = (line) =>
                    line.is_reward_line &&
                    (line.reward_id?.program_id?.id === this.program_id.id ||
                        ["ewallet", "gift_card"].includes(
                            line.reward_id?.program_id?.program_type
                        ));
                const moneyLines = order
                    .getOrderlines()
                    .filter(
                        (line) =>
                            !line.payment_program_id &&
                            this._countsForPoints(line) &&
                            this._inDomain(line) &&
                            !isExcludedReward(line)
                    );
                return roundPrecision(
                    this.reward_point_amount *
                        moneyLines.reduce((total, line) => total + line.linePriceTaxIncluded, 0),
                    0.01,
                    "DOWN"
                );
            }
            case "unit":
                return (
                    this.reward_point_amount *
                    qualifyingLines.reduce((qty, line) => qty + line.getQuantity(), 0)
                );
            default:
                return 0;
        }
    }
}

registry.category("pos_available_models").add(LoyaltyRule.pythonModel, LoyaltyRule);
