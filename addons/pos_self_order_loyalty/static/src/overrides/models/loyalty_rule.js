import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";


export class LoyaltyRule extends Base {
    static pythonModel = "loyalty.rule";

    isConditionSatisfied(order) {
        const applicableLines = this.getApplicableLines(order);
        if (this.minimum_qty > 0) {
            const totalQty = applicableLines.reduce((sum, line) => sum + line.qty, 0);
            if (totalQty < this.minimum_qty) {
                return false;
            }
        }
        if (this.minimum_amount > 0) {
            const taxMode = this.minimum_amount_tax_mode == "incl" ? "total_included" : "total_excluded";
            const totalAmount = applicableLines.reduce((sum, line) => sum + line.prices[taxMode], 0);
            if (totalAmount < this.minimum_amount) {
                return false;
            }
        }
        return true;
    }
    getApplicableLines(order) {
        return order.lines.filter((line) => !line.is_reward_line && (this.any_product || this.valid_product_ids.includes(line.product_id)));
    }
    getPointsToGive(order) {
        const applicableLines = this.getApplicableLines(order);
        switch (this.reward_point_mode) {
            case 'order':
                return this.reward_point_amount;
            case 'money':
                {
                    const totalAmount = applicableLines.reduce((sum, line) => sum + line.prices.total_included, 0);
                    return totalAmount * this.reward_point_amount;
                }
            case 'unit':
                {
                    const totalQty = applicableLines.reduce((sum, line) => sum + line.qty, 0);
                    return totalQty * this.reward_point_amount;
                }
            default:
                return 0;
        }
    }
}

registry.category("pos_available_models").add(LoyaltyRule.pythonModel, LoyaltyRule);
