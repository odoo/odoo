import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { getOrderLineValues } from "@pos_self_order/app/services/card_utils";
import { patch } from "@web/core/utils/patch";


patch(PosOrder.prototype, {
    initState() {
        super.initState();
        this.uiState = {
            ...this.uiState,
            appliedCode: [],
        };
    },
    setPartner(partner) {
        super.setPartner(partner);
        const loyaltyPrograms = this.models['loyalty.program'].filter(program => program.program_type == "loyalty");
        for (const program of loyaltyPrograms) {
            if (program.is_nominative && program.uiState.linkedCard.partner_id?.id !== partner?.id) {
                program.uiState.linkedCard = null;
            }
        }
    },
    updateLoyaltyPoints() {
        const partner = this.getPartner();
        const loyaltyPrograms = this.models['loyalty.program'].filter(program => ["promotion", "buy_x_get_y", "loyalty"].includes(program.program_type));

        for (const program of loyaltyPrograms) {
            const rules = program.rule_ids;
            let pointsDifference = 0;
            if (program.applies_on != "future") {
                // If program applies only on future orders, the backend will update the points after the order is paid
                for (const rule of rules) {
                    if (rule.isConditionSatisfied(this)) {
                        pointsDifference += rule.getPointsToGive(this);
                    }
                }
            }
            for (const line of this.lines) {
                if (line.is_reward_line && line.reward_id.program_id.id === program.id) {
                    pointsDifference -= line.points_cost;
                }
            }
            let card = program.uiState.linkedCard;
            if (!card) {
                card = this.models['loyalty.card'].filter(card => card.program_id.id === program.id);
                if (program.is_nominative) {
                    card = card.filter(card => card.partner_id?.id === partner?.id);
                }
                card = card[0];
                if (!card) {
                    // TODO still not sure about this part
                    card = this.models["loyalty.card"].create({
                        program_id: program,
                        partner_id: partner || false,
                        points: 0,
                    });
                }
                program.uiState.linkedCard = card;
            }
            program.uiState.pointsDifference = pointsDifference;
        }
    },
    removeOrderline(line, deep = true) {
        if (line.is_reward_line) {
            this.updateAppliedCouponCodes();
        }
        return super.removeOrderline(...arguments);
    },
    updateAppliedCouponCodes() {
        const actualCodes = [];
        for (const line of this.lines) {
            if (line.is_reward_line) {
                actualCodes.push(line.uiState.rewardCode);
            }
        }
        this.uiState.appliedCode = actualCodes;
    },
    computeDiscountAmount(reward, points_cost) {
        let getDiscountable;
        switch (reward.discount_applicability) {
            case "order":
                getDiscountable = this._getDiscountableOnOrder.bind(this);
                break;
            case "cheapest":
                getDiscountable = this._getDiscountableOnCheapest.bind(this);
                break;
            case "specific":
                getDiscountable = this._getDiscountableOnSpecific.bind(this);
                break;
            default:
                return;
        }
        let { discountable, discountablePerTax } = getDiscountable(reward);
        let maxDiscount = reward.discount_max_amount || Infinity;
        if (reward.discount_mode === "per_point") {
            maxDiscount = Math.min(maxDiscount, reward.discount * points_cost);
        } else if (reward.discount_mode === "per_order") {
            maxDiscount = Math.min(maxDiscount, reward.discount);
        } else if (reward.discount_mode === "percent") {
            maxDiscount = Math.min(maxDiscount, discountable * (reward.discount / 100));
        } else {
            maxDiscount = 0;
        }
        const discountFactor = discountable ? Math.min(1, maxDiscount / discountable) : 1;
        const discountPerTax = Object.entries(discountablePerTax).reduce((lst, entry) => {
            // Ignore 0 price lines
            if (!entry[1]) {
                return lst;
            }
            let taxIds = entry[0] === "" ? [] : entry[0].split(",").map((str) => parseInt(str));
            taxIds = this.models["account.tax"].filter((tax) => taxIds.includes(tax.id));

            lst.push({
                price_unit: this.currency.round(-(Math.min(this.priceIncl, entry[1]) * discountFactor)),
                tax_ids: taxIds,
            });
            return lst;
        }, []);

        return discountPerTax;
    },
});
