import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.applied_codes = this.applied_codes || [];
        this.disabled_program_ids = this.disabled_program_ids || [];
        this.active_rewards = this.active_rewards || [];
        this.active_payment_programs = this.active_payment_programs || [];
        this._line_discountable_price = this._line_discountable_price || {};
    },
    /**
     * Keep reward lines at the bottom of the cart
     * @returns {PosOrderline[]}
     */
    getOrderlines() {
        const orderlines = super.getOrderlines(...arguments);
        const rewardLines = [];
        const nonRewardLines = [];
        for (const line of orderlines) {
            (line.is_reward_line ? rewardLines : nonRewardLines).push(line);
        }
        return [...nonRewardLines, ...rewardLines];
    },
    /**
     * Whether one of the program's codes has been entered on this order
     * @param {loyalty_program} program
     * @returns {boolean}
     */
    isProgramCodeActivated(program) {
        return (
            program.rule_ids.some((rule) => this.applied_codes.includes(rule.code)) ||
            this.models["loyalty.card"].some(
                (card) =>
                    card.program_id?.id === program.id && this.applied_codes.includes(card.code)
            )
        );
    },
    /**
     * Whether a usage-limited program has already been used its maximum number of times.
     * @param {loyalty_program} program
     * @returns {boolean}
     */
    isProgramUsageExceeded(program) {
        return program.limit_usage && program.total_order_count >= program.max_usage;
    },
    /**
     * Whether the program is available for the order's current pricelist.
     * @param {loyalty_program} program
     * @returns {boolean}
     */
    isProgramPricelistValid(program) {
        return (
            !program.pricelist_ids.length ||
            program.pricelist_ids.some((pricelist) => pricelist.id === this.pricelist_id?.id)
        );
    },
    /**
     * Returns the loaded loyalty programs that are applied automatically,
     * The programs that have their trigger set to auto, are not in
     * this._disabled_programs_ids, are applicable to the current order and have
     * exactly one reward that is a discount.
     * @returns {loyalty_program[]} the automatically applied programs
     */
    get appliedPrograms() {
        return this.models["loyalty.program"].filter((program) => {
            const codeActivated = this.isProgramCodeActivated(program);
            const active =
                program.trigger === "auto" || (program.trigger === "with_code" && codeActivated);
            if (
                !active ||
                (program.applies_on === "future" && !codeActivated) ||
                program.is_nominative ||
                program.is_payment_program ||
                this.disabled_program_ids.includes(program.id) ||
                this.isProgramUsageExceeded(program) ||
                !this.isProgramPricelistValid(program) ||
                program.reward_ids.length !== 1
            ) {
                return false;
            }
            const reward = program.reward_ids[0];
            return reward.reward_type === "discount";
        });
    },
    /**
     * Return a list of the rewards that might be applied on the current order.
     * The method is used by the control button to enable and list the Rewards from
     * the 'Rewards' button.
     * If any rewards are disabled on the order, they will also be included in the list
     * @returns {loyalty_reward[]} the list of rewards that might be applied
     */
    get availableRewards() {
        // A reward is no longer available once it's been claimed: either it produced
        // a reward line, or it was explicitly claimed (in active_rewards) even if it
        // matched no product and so created no line.
        const appliedRewardIds = new Set([
            ...this.getOrderlines()
                .filter((line) => line.is_reward_line)
                .map((line) => line.reward_id?.id),
            ...this.active_rewards.map((entry) => entry.reward_id),
        ]);
        const rewards = [];
        const programs = this.models["loyalty.program"].filter(
            (program) =>
                (program.trigger !== "with_code" || this.isProgramCodeActivated(program)) &&
                (!program.is_nominative || this.partner_id) &&
                !this.isProgramUsageExceeded(program) &&
                this.isProgramPricelistValid(program)
        );
        for (const program of programs) {
            const points = program.getPoints(this);
            for (const reward of program.reward_ids) {
                if (points >= reward.required_points && !appliedRewardIds.has(reward.id)) {
                    rewards.push({ reward: reward, points: points });
                }
            }
        }
        return rewards;
    },
    /**
     * Appply a payment program for the current order and create a new orderline for it
     * If the amount is set, the orderline will have the minimum between the order total
     * and the amount. If the amount is undefined the value will be the minimum between
     * the order total and the program available points
     * @param {loyalty_reward} reward - the payment reward to apply
     * @param {loyalty_card} card - the card being spent from
     * @param {number} [amount] - the amount the user chose to spend, capped by balance and order total
     */
    applyPaymentProgram(reward, card, amount) {
        if (!reward || !card) {
            return;
        }

        for (const line of this.getOrderlines().filter(
            (line) =>
                line.is_reward_line &&
                line.reward_id?.id === reward.id &&
                line.card_id?.id === card.id
        )) {
            line.delete();
        }

        const balance = card.points;
        if (balance <= 0 || !reward.discount) {
            return;
        }

        const available = amount === undefined ? balance : Math.min(amount, balance);
        const maxDiscount = Math.min(this.priceIncl, reward.discount_max_amount || Infinity);
        const paid = Math.min(maxDiscount, reward.discount * available);
        if (paid <= 0) {
            return;
        }

        const discountProduct = reward.discount_line_product_id;
        const details = discountProduct.getTaxDetails({
            overridedValues: {
                price: -paid,
                tax_ids: [],
                special_mode: "total_included",
            },
        });
        const priceUnit = details.raw_total_included;

        this.models["pos.order.line"].create({
            product_id: discountProduct,
            qty: 1,
            price_unit: priceUnit,
            price_type: "manual",
            tax_ids: [],
            is_reward_line: true,
            reward_id: reward,
            card_id: card,
            points_cost: reward.clear_wallet ? balance : paid / reward.discount,
            order_id: this,
        });
    },
    /**
     * Apply a code and add it to the order's applied_codes
     * Check whether it was already applied
     * Check whether a rule with the specific code exists
     * If the program belongs to a nominative program, automatically set
     * the partner ID to the owner of the code.
     * @param {string} code
     * @returns {string} rejection reason or "" for success
     */
    applyCode(code) {
        const card = this.models["loyalty.card"].find((card) => card.code == code);
        const rule = card ? null : this.models["loyalty.rule"].find((r) => r.matchCode(code));
        if (!card && !rule) {
            return {
                success: false,
                program_id: null,
                rejection_message: _t("That card code is invalid (%s).", code),
            };
        }
        const appliedCode = rule ? rule.code : code;
        if (this.applied_codes.includes(appliedCode)) {
            return {
                success: false,
                program_id: null,
                rejection_message: _t("That card code has already been scanned and activated."),
            };
        }
        const program = card?.program_id || rule?.program_id;
        if (program && !this.isProgramPricelistValid(program)) {
            return {
                success: false,
                program_id: null,
                rejection_message: _t("That card program requires a specific pricelist."),
            };
        }
        if (card?.partner_id) {
            if (this.partner_id && this.partner_id != card.partner_id) {
                return {
                    success: false,
                    program_id: null,
                    rejection_message: _t("That card code belongs to someone else."),
                };
            }
            this.partner_id = card.partner_id;
        }

<<<<<<< 7434faa93558d4f46fdda77acd1be4dfc663ea7c
        if (card?.program_id?.is_payment_program) {
            this.active_payment_programs = [
                ...this.active_payment_programs,
                { reward_id: card.program_id.reward_ids[0].id, card_id: card.id },
||||||| 57fad2e46286b74d3832a3c7cea4a84327268224
        // Check if the rule's reward point mode is order then not valid for correction
        if (rule.reward_point_mode === "order") {
            return false;
        }

        // Check if the reward line is part of the rule
        if (!(rule.any_product || rule.validProductIds.has(line._reward_product_id?.id))) {
            return false;
        }

        // Check if the reward line and the rule are associated with the same program
        if (rule.program_id.id !== reward.program_id.id) {
            return false;
        }
        return true;
    },
    /**
     * @returns {number} The points that are left for the given coupon for this order.
     */
    _getRealCouponPoints(coupon_id) {
        let points = 0;
        const dbCoupon = this.models["loyalty.card"].get(coupon_id);
        if (dbCoupon) {
            points += dbCoupon.points;
        }
        Object.values(this.uiState.couponPointChanges).some((pe) => {
            if (pe.coupon_id === coupon_id) {
                if (this.models["loyalty.program"].get(pe.program_id).applies_on !== "future") {
                    points += pe.points;
                }
                // couponPointChanges is not supposed to have a coupon multiple times
                return true;
            }
            return false;
        });
        for (const line of this.getOrderlines()) {
            if (line.is_reward_line && line.coupon_id?.id === coupon_id) {
                points -= line.points_cost;
            }
        }
        return points;
    },
    _programIsApplicable(program) {
        if (
            program.trigger === "auto" &&
            !program.rule_ids.find(
                (rule) =>
                    rule.mode === "auto" || this.uiState.codeActivatedProgramRules.includes(rule.id)
            )
        ) {
            return false;
        }
        if (
            program.trigger === "with_code" &&
            !program.rule_ids.find((rule) =>
                this.uiState.codeActivatedProgramRules.includes(rule.id)
            )
        ) {
            return false;
        }
        if (program.is_nominative && !this.getPartner()) {
            return false;
        }
        if (program.date_from && program.date_from.startOf("day") > DateTime.now()) {
            return false;
        }
        if (program.date_to && program.date_to.endOf("day") < DateTime.now()) {
            return false;
        }
        if (program.limit_usage && program.total_order_count >= program.max_usage) {
            return false;
        }
        if (
            program.pricelist_ids.length > 0 &&
            (!this.pricelist_id ||
                !program.pricelist_ids.some((pl) => pl.id === this.pricelist_id.id))
        ) {
            return false;
        }
        return true;
    },
    isLineValidForLoyaltyPoints(line) {
        // This method should be overriden in other modules
        return true;
    },
    /**
     * Computes how much points each program gives.
     *
     * @param {Array} programs list of loyalty.program
     * @returns {Object} Containing the points gained per program
     */
    pointsForPrograms(programs) {
        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        pointsForProgramsCountedRules = {};
        const orderLines = this.getOrderlines().filter((line) => !line.combo_parent_id);

        const linesPerRule = {};
        for (const line of orderLines) {
            const reward = line.reward_id;
            const isDiscount = reward && reward.reward_type === "discount";
            const rewardProgram = reward && reward.program_id;
            // Skip lines for automatic discounts.
            if (isDiscount && rewardProgram.trigger === "auto") {
                continue;
            }

            if (!this.isLineValidForLoyaltyPoints(line)) {
                continue;
            }
            for (const program of programs) {
                // Skip lines for the current program's discounts.
                if (isDiscount && rewardProgram.id === program.id) {
                    continue;
                }
                for (const rule of program.rule_ids) {
                    // Skip lines to which the rule doesn't apply.
                    if (rule.any_product || rule.validProductIds.has(line.product_id.id)) {
                        if (!linesPerRule[rule.id]) {
                            linesPerRule[rule.id] = [];
                        }
                        linesPerRule[rule.id].push(line);
                    }
                }
            }
        }
        const result = {};
        for (const program of programs) {
            let points = 0;
            const splitPoints = [];
            for (const rule of program.rule_ids) {
                if (
                    rule.mode === "with_code" &&
                    !this.uiState.codeActivatedProgramRules.includes(rule.id)
                ) {
                    continue;
                }
                const linesForRule = linesPerRule[rule.id] ? linesPerRule[rule.id] : [];
                const amountWithTax = linesForRule.reduce(
                    (sum, line) =>
                        sum +
                        (line.combo_line_ids.length > 0
                            ? line.comboTotalPrice
                            : line.prices.total_included),
                    0
                );
                const amountWithoutTax = linesForRule.reduce(
                    (sum, line) =>
                        sum +
                        (line.combo_line_ids.length > 0
                            ? line.comboTotalPriceWithoutTax
                            : line.prices.total_excluded),
                    0
                );
                const amountCheck =
                    (rule.minimum_amount_tax_mode === "incl" && amountWithTax) || amountWithoutTax;
                if (rule.minimum_amount > amountCheck) {
                    continue;
                }
                let totalProductQty = 0;
                let hasValidProduct = false;
                // Only count points for paid lines.
                const qtyPerProduct = {};
                let orderedProductPaid = 0;
                for (const line of orderLines) {
                    if (
                        ((!line.reward_product_id &&
                            (rule.any_product || rule.validProductIds.has(line.product_id.id))) ||
                            (line.reward_product_id &&
                                (rule.any_product ||
                                    rule.validProductIds.has(line._reward_product_id?.id)))) &&
                        !line.ignoreLoyaltyPoints({ program })
                    ) {
                        // We only count reward products from the same program to avoid unwanted feedback loops
                        if (line.is_reward_line) {
                            const reward = line.reward_id;
                            if (
                                program.id === reward.program_id.id ||
                                ["gift_card", "ewallet"].includes(reward.program_id.program_type)
                            ) {
                                continue;
                            }
                        }
                        const lineQty = line._reward_product_id
                            ? -line.getQuantity()
                            : line.getQuantity();
                        if (qtyPerProduct[line._reward_product_id || line.getProduct().id]) {
                            qtyPerProduct[line._reward_product_id || line.getProduct().id] +=
                                lineQty;
                        } else {
                            qtyPerProduct[line._reward_product_id?.id || line.getProduct().id] =
                                lineQty;
                        }
                        orderedProductPaid +=
                            line.combo_line_ids.length > 0
                                ? line.comboTotalPrice
                                : line.prices.total_included;
                        if (!line.is_reward_line) {
                            totalProductQty += lineQty;
                            hasValidProduct = true;
                        }
                    }
                }
                // Skip product-restricted rules when the order contains none of their products.
                if (!rule.any_product && !hasValidProduct) {
                    continue;
                }
                if (totalProductQty < rule.minimum_qty) {
                    // Should also count the points from negative quantities.
                    // For example, when refunding an ewallet payment. See TicketScreen override in this addon.
                    continue;
                }
                if (!(program.id in pointsForProgramsCountedRules)) {
                    pointsForProgramsCountedRules[program.id] = [];
                }
                pointsForProgramsCountedRules[program.id].push(rule.id);
                if (
                    program.applies_on === "future" &&
                    rule.reward_point_split &&
                    rule.reward_point_mode !== "order"
                ) {
                    // In this case we count the points per rule
                    if (rule.reward_point_mode === "unit") {
                        splitPoints.push(
                            ...Array.apply(null, Array(totalProductQty)).map((_) => ({
                                points: rule.reward_point_amount,
                            }))
                        );
                    } else if (rule.reward_point_mode === "money") {
                        for (const line of orderLines) {
                            if (
                                line.is_reward_line ||
                                !rule.validProductIds.has(line.product_id.id) ||
                                line.getQuantity() <= 0 ||
                                line.ignoreLoyaltyPoints({ program })
                            ) {
                                continue;
                            }
                            const pointsPerUnit = ProductPrice.round(
                                (rule.reward_point_amount * line.prices.total_included) /
                                    line.getQuantity()
                            );
                            if (pointsPerUnit > 0) {
                                splitPoints.push(
                                    ...Array.apply(null, Array(line.getQuantity())).map(() => {
                                        if (line._gift_barcode && line.getQuantity() == 1) {
                                            return {
                                                points: pointsPerUnit,
                                                barcode: line._gift_barcode,
                                                giftCardId: line._gift_card_id.id,
                                            };
                                        }
                                        return { points: pointsPerUnit };
                                    })
                                );
                            }
                        }
                    }
                } else {
                    // In this case we add on to the global point count
                    if (rule.reward_point_mode === "order") {
                        points += rule.reward_point_amount;
                    } else if (rule.reward_point_mode === "money") {
                        // NOTE: unlike in sale_loyalty this performs a round half-up instead of round down
                        points += ProductPrice.round(rule.reward_point_amount * orderedProductPaid);
                    } else if (rule.reward_point_mode === "unit") {
                        points += rule.reward_point_amount * totalProductQty;
                    }
                }
            }
            const res = points || program.program_type === "coupons" ? [{ points }] : [];
            if (splitPoints.length) {
                res.push(...splitPoints);
            }
            result[program.id] = res;
        }
        return result;
    },
    /**
     * @returns {Array} List of lines composing the global discount
     */
    _getGlobalDiscountLines() {
        return this.getOrderlines().filter(
            (line) => line.reward_id && line.reward_id.is_global_discount
        );
    },
    /**
     * Returns the number of product items in the order based on the given rule.
     * @param {*} rule
     */
    _computeNItems(rule) {
        return this._get_regular_order_lines().reduce((nItems, line) => {
            let increment = 0;
            if (rule.any_product || rule.validProductIds.has(line.product_id.id)) {
                increment = line.getQuantity();
            }
            return nItems + increment;
        }, 0);
    },
    /**
     * Checks whether this order is allowed to generate rewards
     * from the given coupon program.
     * @param {*} couponProgram
     */
    _canGenerateRewards(couponProgram, orderTotalWithTax, orderTotalWithoutTax) {
        for (const rule of couponProgram.rule_ids) {
            const amountToCompare =
                rule.minimum_amount_tax_mode == "incl" ? orderTotalWithTax : orderTotalWithoutTax;
            if (rule.minimum_amount > amountToCompare) {
                return false;
            }
            const nItems = this._computeNItems(rule);
            if (rule.minimum_qty > nItems) {
                return false;
            }
            if (
                !rule.any_product &&
                !this._get_regular_order_lines().some((line) =>
                    rule.validProductIds.has(line.product_id.id)
                )
            ) {
                return false;
            }
        }
        return true;
    },
    /**
     * @param {Integer} coupon_id (optional) Coupon id
     * @param {Integer} program_id (optional) Program id
     * @returns {Array} List of {Object} containing the coupon_id and reward keys
     */
    getClaimableRewards(coupon_id = false, program_id = false, auto = false) {
        const couponPointChanges = this.uiState.couponPointChanges;
        const excludedCouponIds = Object.keys(couponPointChanges)
            .filter((id) => couponPointChanges[id].manual && couponPointChanges[id].existing_code)
            .map((id) => couponPointChanges[id].coupon_id);

        const allCouponPrograms = Object.values(this.uiState.couponPointChanges)
            .filter((pe) => !excludedCouponIds.includes(pe.coupon_id))
            .map((pe) => ({
                program_id: pe.program_id,
                coupon_id: pe.coupon_id,
            }))
            .concat(
                this._code_activated_coupon_ids.map((coupon) => ({
                    program_id: coupon.program_id.id,
                    coupon_id: coupon.id,
                }))
            );
        const result = [];
        const totalWithTax = this.priceIncl;
        const totalWithoutTax = this.priceExcl;
        const totalIsZero = totalWithTax === 0;
        const globalDiscountLines = this._getGlobalDiscountLines();
        const globalDiscountPercent = globalDiscountLines.length
            ? globalDiscountLines[0].reward_id.discount
            : 0;
        for (const couponProgram of allCouponPrograms) {
            const program = this.models["loyalty.program"].get(couponProgram.program_id);
            if (
                program.pricelist_ids.length > 0 &&
                (!this.pricelist_id ||
                    !program.pricelist_ids.some((pl) => pl.id === this.pricelist_id.id))
            ) {
                continue;
            }
            if (program.trigger == "with_code") {
                // For coupon programs, the rules become conditions.
                // Points to purchase rewards will only come from the scanned coupon.
                if (!this._canGenerateRewards(program, totalWithTax, totalWithoutTax)) {
                    continue;
                }
            }
            if (
                (coupon_id && couponProgram.coupon_id !== coupon_id) ||
                (program_id && couponProgram.program_id !== program_id)
            ) {
                continue;
            }
            const points = this._getRealCouponPoints(couponProgram.coupon_id);
            for (const reward of program.reward_ids) {
                if (points < reward.required_points) {
                    continue;
                }
                // Skip already applied rewards: 'coupons' programs, and non-payment
                // discounts when auto-claiming, to avoid stacking them
                const isPaymentProgram = ["ewallet", "gift_card"].includes(
                    reward.program_id.program_type
                );
                if (
                    (reward.program_id.program_type === "coupons" ||
                        (auto && reward.reward_type === "discount" && !isPaymentProgram)) &&
                    this.lines.some((rewardline) => rewardline.reward_id?.id === reward.id)
                ) {
                    continue;
                }
                if (auto && this.uiState.disabledRewards.has(reward.id)) {
                    continue;
                }
                // Try to filter out rewards that will not be claimable anyway.
                if (reward.is_global_discount && reward.discount <= globalDiscountPercent) {
                    continue;
                }
                if (reward.reward_type === "discount" && totalIsZero) {
                    continue;
                }
                let unclaimedQty;
                let rewardProduct;
                if (reward.reward_type === "product") {
                    if (!reward.multi_product) {
                        rewardProduct = reward.reward_product_id;
                    } else if (auto) {
                        // A multi product reward is claimed on the line being worked on.
                        rewardProduct = reward.reward_product_ids.find(
                            (product) => product.id === this.getSelectedOrderline()?.product_id.id
                        );
                    }
                    if (!rewardProduct) {
                        continue;
                    }
                    unclaimedQty = this._computeUnclaimedFreeProductQty(
                        reward,
                        couponProgram.coupon_id,
                        rewardProduct,
                        points
                    );
                    if (!unclaimedQty || unclaimedQty <= 0) {
                        continue;
                    }
                }
                result.push({
                    coupon_id: couponProgram.coupon_id,
                    reward: reward,
                    potentialQty: unclaimedQty,
                    product: rewardProduct,
                });
            }
        }
        return result;
    },
    /**
     * TODO JCB: make the second parameter not id, but the loyalty.card object itself.
     * Applies a reward to the order, `pos.updateRewards` is expected to be called right after.
     *
     * @param {loyalty.reward} reward
     * @param {Integer} coupon_id
     * @param {Object} args Reward options
     * @returns True if everything went right or an error message
     */
    _applyReward(reward, coupon_id, args) {
        if (this._getRealCouponPoints(coupon_id) < reward.required_points) {
            return _t("There are not enough points on the coupon to claim this reward.");
        }
        if (reward.is_global_discount) {
            const globalDiscountLines = this._getGlobalDiscountLines();
            if (globalDiscountLines.length) {
                const rewardId = globalDiscountLines[0].reward_id;
                if (rewardId != reward.id && rewardId.discount >= reward.discount) {
                    return _t("A better global discount is already applied.");
                } else if (rewardId != rewardId.id) {
                    for (const line of globalDiscountLines) {
                        line.delete();
                    }
                }
            }
        }
        args = args || {};
        const rewardLines = this._getRewardLineValues({
            reward: reward,
            coupon_id: coupon_id,
            product: args["product"] || null,
            price: args["price"] || null,
            quantity: args["quantity"] || null,
            cost: args["cost"] || null,
        });
        if (!Array.isArray(rewardLines)) {
            return rewardLines; // Returned an error.
        }
        if (!rewardLines.length) {
            return _t("The reward could not be applied.");
        }
        for (const rewardLine of rewardLines) {
            this.applyRewardLine(rewardLine);
        }
        return true;
    },
    applyRewardLine(rewardLine) {
        const prepareRewards = {
            ...rewardLine,
            reward_id: rewardLine.reward_id,
            coupon_id: this.models["loyalty.card"].get(rewardLine.coupon_id),
            tax_ids: rewardLine.tax_ids.map((tax) => ["link", tax]),
        };
        this.models["pos.order.line"].create({
            ...prepareRewards,
            order_id: this,
            price_type: "manual",
        });
    },
    /**
     * Checks if there are any existing manual changes or new coupon additions for the given coupon code
     */
    duplicateCouponChanges(code) {
        return Object.keys(this.uiState.couponPointChanges).some((key) => {
            const change = this.uiState.couponPointChanges[key];
            return (
                (change.existing_code === code && change.manual) ||
                (change.code === code && change.coupon_id < 0)
            );
        });
    },
    /**
     * Processes a gift card by creating a new gift card.
     *
     * @param {String} newGiftCardCode gift card code as a string if new gift card to be created.
     * @param {number} points number of points to assign to the gift card.
     */
    processGiftCard(newGiftCardCode, points, expirationDate) {
        const partner_id = this.partner_id?.id || false;
        const product_id = this.getSelectedOrderline().product_id.id;
        const program =
            this.getSelectedOrderline()._e_wallet_program_id ||
            this.models["loyalty.program"].find((p) => p.program_type === "gift_card");

        let couponId;
        const couponData = {
            program_id: program?.id,
            points: points,
            manual: true,
            product_id: product_id,
        };

        // Fetch all coupon_ids for the specified points and not manually created, that are associated with the gift card program
        const applicableCouponIds = Object.keys(this.uiState.couponPointChanges).filter((key) => {
            const change = this.uiState.couponPointChanges[key];
            return (
                change.points === points &&
                change.program_id === program.id &&
                change.product_id === product_id &&
                !change.manual
            );
        });

        if (newGiftCardCode) {
            couponId = applicableCouponIds.shift() || loyaltyIdsGenerator();
            couponData.coupon_id = couponId;
            couponData.code = newGiftCardCode;
            couponData.partner_id = partner_id;
            couponData.expiration_date = expirationDate;
        }

        this.uiState.couponPointChanges[couponId] = couponData;
    },
    /**
     * @param {loyalty.reward} reward
     * @returns the discountable and discountable per tax for this discount on order reward.
     */
    _getDiscountableOnOrder(reward) {
        let discountable = 0;
        const discountablePerTax = {};
        for (const line of this.getOrderlines()) {
            if (!line.getQuantity()) {
                continue;
            }
            const taxKey = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
                ? line.tax_ids.map((t) => t.id)
                : line.tax_ids.filter((t) => t.amount_type !== "fixed").map((t) => t.id);
            discountable += line.prices.total_included;
            if (!discountablePerTax[taxKey]) {
                discountablePerTax[taxKey] = 0;
            }
            discountablePerTax[taxKey] += line.basePrice;
        }
        return { discountable, discountablePerTax };
    },
    /**
     * @param {loyalty.reward} reward
     * @returns the cheapest line from all the lines where the program is applicable
     */
    _getCheapestLine(reward) {
        const applicableProductIds = new Set(reward.all_discount_product_ids.map((p) => p.id));
        const filtered_lines = this.getOrderlines().filter(
            (line) =>
                !line.combo_parent_id &&
                !line.reward_id &&
                line.getQuantity() &&
                applicableProductIds.has(line.getProduct().id)
        );
        return filtered_lines.toSorted(
            (lineA, lineB) => lineA.comboTotalPrice / lineA.qty - lineB.comboTotalPrice / lineB.qty
        )[0];
    },
    /**
     * @returns the discountable and discountable per tax for this discount on cheapest reward.
     */
    _getDiscountableOnCheapest(reward) {
        const cheapestLine = this._getCheapestLine(reward);
        if (!cheapestLine) {
            return { discountable: 0, discountablePerTax: {} };
        }
        const taxKey = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
            ? cheapestLine.tax_ids.map((t) => t.id)
            : cheapestLine.tax_ids.filter((t) => t.amount_type !== "fixed").map((t) => t.id);
        return {
            discountable: cheapestLine.comboTotalBasePrice,
            discountablePerTax: Object.fromEntries([[taxKey, cheapestLine.comboTotalBasePrice]]),
        };
    },
    /**
     * @param {loyalty.reward} reward
     * @returns all lines to which the reward applies.
     */
    _getSpecificDiscountableLines(reward) {
        const discountableLines = [];
        const applicableProductIds = new Set(reward.all_discount_product_ids.map((p) => p.id));
        for (const line of this.getOrderlines()) {
            if (!line.getQuantity()) {
                continue;
            }
            if (
                applicableProductIds.has(line.getProduct().id) ||
                applicableProductIds.has(line._reward_product_id?.id)
            ) {
                discountableLines.push(line);
            }
        }
        return discountableLines;
    },
    /**
     * For a 'specific' type of discount it is more complicated as we have to make sure that we never
     *  discount more than what is available on a per line basis.
     * @param {loyalty.reward} reward
     * @returns the discountable and discountable per tax for this discount on specific reward.
     */
    _getDiscountableOnSpecific(reward) {
        const applicableProductIds = new Set(reward.all_discount_product_ids.map((p) => p.id));
        const linesToDiscount = [];
        const discountLinesPerReward = {};
        const orderLines = this.getOrderlines();
        const orderProducts = orderLines.map((line) => line.product_id.id);
        const remainingAmountPerLine = {};
        for (const line of orderLines) {
            if (!line.getQuantity() || !line.price_unit) {
                continue;
            }
            remainingAmountPerLine[line.uuid] = line.prices.total_included;
            const product_id = line.combo_parent_id?.product_id.id || line.getProduct().id;
            if (
                applicableProductIds.has(product_id) ||
                (line._reward_product_id && applicableProductIds.has(line._reward_product_id.id))
            ) {
                linesToDiscount.push(line);
            } else if (line.reward_id) {
                const lineReward = line.reward_id;
                const lineRewardApplicableProductsIds = new Set(
                    lineReward.all_discount_product_ids.map((p) => p.id)
                );
                if (
                    lineReward.id === reward.id ||
                    (orderProducts.some(
                        (product) =>
                            lineRewardApplicableProductsIds.has(product) &&
                            applicableProductIds.has(product)
                    ) &&
                        lineReward.reward_type === "discount" &&
                        lineReward.discount_mode != "percent")
                ) {
                    linesToDiscount.push(line);
                }
                if (!discountLinesPerReward[line.reward_identifier_code]) {
                    discountLinesPerReward[line.reward_identifier_code] = [];
                }
                discountLinesPerReward[line.reward_identifier_code].push(line);
            }
        }

        let cheapestLine = false;
        for (const lines of Object.values(discountLinesPerReward)) {
            const lineReward = lines[0].reward_id;
            if (lineReward.reward_type !== "discount") {
                continue;
            }
            let discountedLines = orderLines;
            if (lineReward.discount_applicability === "cheapest") {
                cheapestLine = cheapestLine || this._getCheapestLine(lineReward);
                discountedLines = [cheapestLine];
            } else if (lineReward.discount_applicability === "specific") {
                discountedLines = this._getSpecificDiscountableLines(lineReward);
            }
            if (!discountedLines.length) {
                continue;
            }
            if (lineReward.discount_mode === "percent") {
                const discount = lineReward.discount / 100;
                for (const line of discountedLines) {
                    if (line.reward_id) {
                        continue;
                    }
                    let discountedAmount = 0;
                    if (lineReward.discount_applicability === "cheapest") {
                        discountedAmount =
                            (-remainingAmountPerLine[line.uuid] * discount) / line.getQuantity();
                    } else {
                        discountedAmount = -remainingAmountPerLine[line.uuid] * discount;
                    }
                    if (lineReward.discount_max_amount && lineReward.discount_max_amount > 0) {
                        discountedAmount = Math.max(
                            discountedAmount,
                            -lineReward.discount_max_amount
                        );
                    }
                    remainingAmountPerLine[line.uuid] += discountedAmount;
                }
            }
        }

        let discountable = 0;
        const discountablePerTax = {};
        for (const line of linesToDiscount) {
            discountable += remainingAmountPerLine[line.uuid];
            const taxKey = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
                ? line.tax_ids.map((t) => t.id)
                : line.tax_ids.filter((t) => t.amount_type !== "fixed").map((t) => t.id);
            if (!discountablePerTax[taxKey]) {
                discountablePerTax[taxKey] = 0;
            }
            discountablePerTax[taxKey] +=
                line.basePrice * (remainingAmountPerLine[line.uuid] / line.prices.total_included);
        }
        return { discountable, discountablePerTax };
    },
    /**
     * @param {Object} args See `_applyReward`
     * @returns {Array} List of values to create the reward lines
     */
    _getRewardLineValues(args) {
        const reward = args["reward"];
        if (reward.reward_type === "discount") {
            return this._getRewardLineValuesDiscount(args);
        } else if (reward.reward_type === "product") {
            return this._getRewardLineValuesProduct(args);
        }
        // NOTE: we may reach this step if for some reason there is a free shipping reward
        return [];
    },
    /**
     * @param {Object} args See `_applyReward`
     * @returns {Array} List of values to create the discount lines
     */
    _getRewardLineValuesDiscount(args) {
        //LINK
        const reward = args["reward"];
        const coupon_id = args["coupon_id"];
        const rewardAppliesTo = reward.discount_applicability;
        let getDiscountable;
        if (rewardAppliesTo === "order") {
            getDiscountable = this._getDiscountableOnOrder.bind(this);
        } else if (rewardAppliesTo === "cheapest") {
            getDiscountable = this._getDiscountableOnCheapest.bind(this);
        } else if (rewardAppliesTo === "specific") {
            getDiscountable = this._getDiscountableOnSpecific.bind(this);
        }
        if (!getDiscountable) {
            return _t("Unknown discount type");
        }
        let { discountable, discountablePerTax } = getDiscountable(reward);
        discountable = Math.min(this.priceIncl, discountable);
        if (floatIsZero(discountable)) {
            return [];
        }
        let maxDiscount = reward.discount_max_amount || Infinity;
        if (reward.discount_mode === "per_point") {
            // Rewards cannot be partially offered to customers
            const points = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
                ? this._getRealCouponPoints(coupon_id)
                : Math.floor(this._getRealCouponPoints(coupon_id) / reward.required_points) *
                  reward.required_points;
            maxDiscount = Math.min(maxDiscount, reward.discount * points);
        } else if (reward.discount_mode === "per_order") {
            maxDiscount = Math.min(maxDiscount, reward.discount);
        } else if (reward.discount_mode === "percent") {
            maxDiscount = Math.min(maxDiscount, discountable * (reward.discount / 100));
        }
        const rewardCode = _newRandomRewardCode();
        let pointCost = reward.clear_wallet
            ? this._getRealCouponPoints(coupon_id)
            : reward.required_points;
        if (reward.discount_mode === "per_point" && !reward.clear_wallet) {
            pointCost = Math.min(maxDiscount, discountable) / reward.discount;
        }
        // These are considered payments and do not require to be either taxed or split by tax
        const discountProduct = reward.discount_line_product_id;
        if (["ewallet", "gift_card"].includes(reward.program_id.program_type)) {
            const baseLine = discountProduct.getBaseLine({
                overridedValues: {
                    tax_ids: discountProduct.taxes_id,
                    price_unit: -Math.min(maxDiscount, discountable),
                    quantity: 1,
                    special_mode: "total_included",
                },
            });
            accountTaxHelpers.add_tax_details_in_base_line(baseLine, this.company);
            accountTaxHelpers.round_base_lines_tax_details([baseLine], this.company);
            accountTaxHelpers.fix_base_lines_tax_details_on_manual_tax_amounts(
                [baseLine],
                this.company
            );
            const extraTaxData = accountTaxHelpers.export_base_line_extra_tax_data(baseLine);

            return [
                {
                    product_id: discountProduct,
                    price_unit: baseLine.price_unit,
                    qty: 1,
                    reward_id: reward,
                    is_reward_line: true,
                    coupon_id: coupon_id,
                    points_cost: pointCost,
                    reward_identifier_code: rewardCode,
                    tax_ids: discountProduct.taxes_id,
                    extra_tax_data: extraTaxData,
                },
=======
        // Check if the rule's reward point mode is order then not valid for correction
        if (rule.reward_point_mode === "order") {
            return false;
        }

        // Check if the reward line is part of the rule
        if (!(rule.any_product || rule.validProductIds.has(line._reward_product_id?.id))) {
            return false;
        }

        // Check if the reward line and the rule are associated with the same program
        if (rule.program_id.id !== reward.program_id.id) {
            return false;
        }
        return true;
    },
    /**
     * @returns {number} The points that are left for the given coupon for this order.
     */
    _getRealCouponPoints(coupon_id) {
        let points = 0;
        const dbCoupon = this.models["loyalty.card"].get(coupon_id);
        if (dbCoupon) {
            points += dbCoupon.points;
        }
        Object.values(this.uiState.couponPointChanges).some((pe) => {
            if (pe.coupon_id === coupon_id) {
                if (this.models["loyalty.program"].get(pe.program_id).applies_on !== "future") {
                    points += pe.points;
                }
                // couponPointChanges is not supposed to have a coupon multiple times
                return true;
            }
            return false;
        });
        for (const line of this.getOrderlines()) {
            if (line.is_reward_line && line.coupon_id?.id === coupon_id) {
                points -= line.points_cost;
            }
        }
        return points;
    },
    _programIsApplicable(program) {
        if (
            program.trigger === "auto" &&
            !program.rule_ids.find(
                (rule) =>
                    rule.mode === "auto" || this.uiState.codeActivatedProgramRules.includes(rule.id)
            )
        ) {
            return false;
        }
        if (
            program.trigger === "with_code" &&
            !program.rule_ids.find((rule) =>
                this.uiState.codeActivatedProgramRules.includes(rule.id)
            )
        ) {
            return false;
        }
        if (program.is_nominative && !this.getPartner()) {
            return false;
        }
        if (program.date_from && program.date_from.startOf("day") > DateTime.now()) {
            return false;
        }
        if (program.date_to && program.date_to.endOf("day") < DateTime.now()) {
            return false;
        }
        if (program.limit_usage && program.total_order_count >= program.max_usage) {
            return false;
        }
        if (
            program.pricelist_ids.length > 0 &&
            (!this.pricelist_id ||
                !program.pricelist_ids.some((pl) => pl.id === this.pricelist_id.id))
        ) {
            return false;
        }
        return true;
    },
    isLineValidForLoyaltyPoints(line) {
        // This method should be overriden in other modules
        return true;
    },
    /**
     * Computes how much points each program gives.
     *
     * @param {Array} programs list of loyalty.program
     * @returns {Object} Containing the points gained per program
     */
    pointsForPrograms(programs) {
        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        pointsForProgramsCountedRules = {};
        const orderLines = this.getOrderlines().filter((line) => !line.combo_parent_id);

        const linesPerRule = {};
        for (const line of orderLines) {
            const reward = line.reward_id;
            const isDiscount = reward && reward.reward_type === "discount";
            const rewardProgram = reward && reward.program_id;
            // Skip lines for automatic discounts.
            if (isDiscount && rewardProgram.trigger === "auto") {
                continue;
            }

            if (!this.isLineValidForLoyaltyPoints(line)) {
                continue;
            }
            for (const program of programs) {
                // Skip lines for the current program's discounts.
                if (isDiscount && rewardProgram.id === program.id) {
                    continue;
                }
                for (const rule of program.rule_ids) {
                    // Skip lines to which the rule doesn't apply.
                    if (rule.any_product || rule.validProductIds.has(line.product_id.id)) {
                        if (!linesPerRule[rule.id]) {
                            linesPerRule[rule.id] = [];
                        }
                        linesPerRule[rule.id].push(line);
                    }
                }
            }
        }
        const result = {};
        for (const program of programs) {
            let points = 0;
            const splitPoints = [];
            for (const rule of program.rule_ids) {
                if (
                    rule.mode === "with_code" &&
                    !this.uiState.codeActivatedProgramRules.includes(rule.id)
                ) {
                    continue;
                }
                const linesForRule = linesPerRule[rule.id] ? linesPerRule[rule.id] : [];
                const amountWithTax = linesForRule.reduce(
                    (sum, line) =>
                        sum +
                        (line.combo_line_ids.length > 0
                            ? line.comboTotalPrice
                            : line.prices.total_included),
                    0
                );
                const amountWithoutTax = linesForRule.reduce(
                    (sum, line) =>
                        sum +
                        (line.combo_line_ids.length > 0
                            ? line.comboTotalPriceWithoutTax
                            : line.prices.total_excluded),
                    0
                );
                const amountCheck =
                    (rule.minimum_amount_tax_mode === "incl" && amountWithTax) || amountWithoutTax;
                if (rule.minimum_amount > amountCheck) {
                    continue;
                }
                let totalProductQty = 0;
                let hasValidProduct = false;
                // Only count points for paid lines.
                const qtyPerProduct = {};
                let orderedProductPaid = 0;
                for (const line of orderLines) {
                    if (
                        ((!line.reward_product_id &&
                            (rule.any_product || rule.validProductIds.has(line.product_id.id))) ||
                            (line.reward_product_id &&
                                (rule.any_product ||
                                    rule.validProductIds.has(line._reward_product_id?.id)))) &&
                        !line.ignoreLoyaltyPoints({ program })
                    ) {
                        // We only count reward products from the same program to avoid unwanted feedback loops
                        if (line.is_reward_line) {
                            const reward = line.reward_id;
                            if (
                                program.id === reward.program_id.id ||
                                ["gift_card", "ewallet"].includes(reward.program_id.program_type)
                            ) {
                                continue;
                            }
                        }
                        const lineQty = line._reward_product_id
                            ? -line.getQuantity()
                            : line.getQuantity();
                        if (qtyPerProduct[line._reward_product_id || line.getProduct().id]) {
                            qtyPerProduct[line._reward_product_id || line.getProduct().id] +=
                                lineQty;
                        } else {
                            qtyPerProduct[line._reward_product_id?.id || line.getProduct().id] =
                                lineQty;
                        }
                        orderedProductPaid +=
                            line.combo_line_ids.length > 0
                                ? line.comboTotalPrice
                                : line.prices.total_included;
                        if (!line.is_reward_line) {
                            totalProductQty += lineQty;
                            hasValidProduct = true;
                        }
                    }
                }
                // Skip product-restricted rules when the order contains none of their products.
                if (!rule.any_product && !hasValidProduct) {
                    continue;
                }
                if (totalProductQty < rule.minimum_qty) {
                    // Should also count the points from negative quantities.
                    // For example, when refunding an ewallet payment. See TicketScreen override in this addon.
                    continue;
                }
                if (!(program.id in pointsForProgramsCountedRules)) {
                    pointsForProgramsCountedRules[program.id] = [];
                }
                pointsForProgramsCountedRules[program.id].push(rule.id);
                if (
                    program.applies_on === "future" &&
                    rule.reward_point_split &&
                    rule.reward_point_mode !== "order"
                ) {
                    // In this case we count the points per rule
                    if (rule.reward_point_mode === "unit") {
                        splitPoints.push(
                            ...Array.apply(null, Array(totalProductQty)).map((_) => ({
                                points: rule.reward_point_amount,
                            }))
                        );
                    } else if (rule.reward_point_mode === "money") {
                        for (const line of orderLines) {
                            if (
                                line.is_reward_line ||
                                !rule.validProductIds.has(line.product_id.id) ||
                                line.getQuantity() <= 0 ||
                                line.ignoreLoyaltyPoints({ program })
                            ) {
                                continue;
                            }
                            const pointsPerUnit = ProductPrice.round(
                                (rule.reward_point_amount * line.prices.total_included) /
                                    line.getQuantity()
                            );
                            if (pointsPerUnit > 0) {
                                splitPoints.push(
                                    ...Array.apply(null, Array(line.getQuantity())).map(() => {
                                        if (line._gift_barcode && line.getQuantity() == 1) {
                                            return {
                                                points: pointsPerUnit,
                                                barcode: line._gift_barcode,
                                                giftCardId: line._gift_card_id.id,
                                            };
                                        }
                                        return { points: pointsPerUnit };
                                    })
                                );
                            }
                        }
                    }
                } else {
                    // In this case we add on to the global point count
                    if (rule.reward_point_mode === "order") {
                        points += rule.reward_point_amount;
                    } else if (rule.reward_point_mode === "money") {
                        // NOTE: unlike in sale_loyalty this performs a round half-up instead of round down
                        points += ProductPrice.round(rule.reward_point_amount * orderedProductPaid);
                    } else if (rule.reward_point_mode === "unit") {
                        points += rule.reward_point_amount * totalProductQty;
                    }
                }
            }
            const res = points || program.program_type === "coupons" ? [{ points }] : [];
            if (splitPoints.length) {
                res.push(...splitPoints);
            }
            result[program.id] = res;
        }
        return result;
    },
    /**
     * @returns {Array} List of lines composing the global discount
     */
    _getGlobalDiscountLines() {
        return this.getOrderlines().filter(
            (line) => line.reward_id && line.reward_id.is_global_discount
        );
    },
    /**
     * Returns the number of product items in the order based on the given rule.
     * @param {*} rule
     */
    _computeNItems(rule) {
        return this._get_regular_order_lines().reduce((nItems, line) => {
            let increment = 0;
            if (rule.any_product || rule.validProductIds.has(line.product_id.id)) {
                increment = line.getQuantity();
            }
            return nItems + increment;
        }, 0);
    },
    /**
     * Checks whether this order is allowed to generate rewards
     * from the given coupon program.
     * @param {*} couponProgram
     */
    _canGenerateRewards(couponProgram, orderTotalWithTax, orderTotalWithoutTax) {
        for (const rule of couponProgram.rule_ids) {
            const amountToCompare =
                rule.minimum_amount_tax_mode == "incl" ? orderTotalWithTax : orderTotalWithoutTax;
            if (rule.minimum_amount > amountToCompare) {
                return false;
            }
            const nItems = this._computeNItems(rule);
            if (rule.minimum_qty > nItems) {
                return false;
            }
            if (
                !rule.any_product &&
                !this._get_regular_order_lines().some((line) =>
                    rule.validProductIds.has(line.product_id.id)
                )
            ) {
                return false;
            }
        }
        return true;
    },
    /**
     * @param {Integer} coupon_id (optional) Coupon id
     * @param {Integer} program_id (optional) Program id
     * @returns {Array} List of {Object} containing the coupon_id and reward keys
     */
    getClaimableRewards(coupon_id = false, program_id = false, auto = false) {
        const couponPointChanges = this.uiState.couponPointChanges;
        const excludedCouponIds = Object.keys(couponPointChanges)
            .filter((id) => couponPointChanges[id].manual && couponPointChanges[id].existing_code)
            .map((id) => couponPointChanges[id].coupon_id);

        const allCouponPrograms = Object.values(this.uiState.couponPointChanges)
            .filter((pe) => !excludedCouponIds.includes(pe.coupon_id))
            .map((pe) => ({
                program_id: pe.program_id,
                coupon_id: pe.coupon_id,
            }))
            .concat(
                this._code_activated_coupon_ids.map((coupon) => ({
                    program_id: coupon.program_id.id,
                    coupon_id: coupon.id,
                }))
            );
        const result = [];
        const totalWithTax = this.priceIncl;
        const totalWithoutTax = this.priceExcl;
        const totalIsZero = totalWithTax === 0;
        const globalDiscountLines = this._getGlobalDiscountLines();
        const globalDiscountPercent = globalDiscountLines.length
            ? globalDiscountLines[0].reward_id.discount
            : 0;
        for (const couponProgram of allCouponPrograms) {
            const program = this.models["loyalty.program"].get(couponProgram.program_id);
            if (
                program.pricelist_ids.length > 0 &&
                (!this.pricelist_id ||
                    !program.pricelist_ids.some((pl) => pl.id === this.pricelist_id.id))
            ) {
                continue;
            }
            if (program.trigger == "with_code") {
                // For coupon programs, the rules become conditions.
                // Points to purchase rewards will only come from the scanned coupon.
                if (!this._canGenerateRewards(program, totalWithTax, totalWithoutTax)) {
                    continue;
                }
            }
            if (
                (coupon_id && couponProgram.coupon_id !== coupon_id) ||
                (program_id && couponProgram.program_id !== program_id)
            ) {
                continue;
            }
            const points = this._getRealCouponPoints(couponProgram.coupon_id);
            for (const reward of program.reward_ids) {
                if (points < reward.required_points) {
                    continue;
                }
                // Skip already applied rewards: 'coupons' programs, and non-payment
                // discounts when auto-claiming, to avoid stacking them
                const isPaymentProgram = ["ewallet", "gift_card"].includes(
                    reward.program_id.program_type
                );
                if (
                    (reward.program_id.program_type === "coupons" ||
                        (auto && reward.reward_type === "discount" && !isPaymentProgram)) &&
                    this.lines.some((rewardline) => rewardline.reward_id?.id === reward.id)
                ) {
                    continue;
                }
                if (auto && this.uiState.disabledRewards.has(reward.id)) {
                    continue;
                }
                // Try to filter out rewards that will not be claimable anyway.
                if (reward.is_global_discount && reward.discount <= globalDiscountPercent) {
                    continue;
                }
                if (reward.reward_type === "discount" && totalIsZero) {
                    continue;
                }
                let unclaimedQty;
                let rewardProduct;
                if (reward.reward_type === "product") {
                    if (!reward.multi_product) {
                        rewardProduct = reward.reward_product_id;
                    } else if (auto) {
                        // A multi product reward is claimed on the line being worked on.
                        rewardProduct = reward.reward_product_ids.find(
                            (product) => product.id === this.getSelectedOrderline()?.product_id.id
                        );
                    }
                    if (!rewardProduct) {
                        continue;
                    }
                    unclaimedQty = this._computeUnclaimedFreeProductQty(
                        reward,
                        couponProgram.coupon_id,
                        rewardProduct,
                        points
                    );
                    if (!unclaimedQty || unclaimedQty <= 0) {
                        continue;
                    }
                }
                result.push({
                    coupon_id: couponProgram.coupon_id,
                    reward: reward,
                    potentialQty: unclaimedQty,
                    product: rewardProduct,
                });
            }
        }
        return result;
    },
    /**
     * TODO JCB: make the second parameter not id, but the loyalty.card object itself.
     * Applies a reward to the order, `pos.updateRewards` is expected to be called right after.
     *
     * @param {loyalty.reward} reward
     * @param {Integer} coupon_id
     * @param {Object} args Reward options
     * @returns True if everything went right or an error message
     */
    _applyReward(reward, coupon_id, args) {
        if (this._getRealCouponPoints(coupon_id) < reward.required_points) {
            return _t("There are not enough points on the coupon to claim this reward.");
        }
        if (reward.is_global_discount) {
            const globalDiscountLines = this._getGlobalDiscountLines();
            if (globalDiscountLines.length) {
                const rewardId = globalDiscountLines[0].reward_id;
                if (rewardId != reward.id && rewardId.discount >= reward.discount) {
                    return _t("A better global discount is already applied.");
                } else if (rewardId != rewardId.id) {
                    for (const line of globalDiscountLines) {
                        line.delete();
                    }
                }
            }
        }
        args = args || {};
        const rewardLines = this._getRewardLineValues({
            reward: reward,
            coupon_id: coupon_id,
            product: args["product"] || null,
            price: args["price"] || null,
            quantity: args["quantity"] || null,
            cost: args["cost"] || null,
        });
        if (!Array.isArray(rewardLines)) {
            return rewardLines; // Returned an error.
        }
        if (!rewardLines.length) {
            return _t("The reward could not be applied.");
        }
        for (const rewardLine of rewardLines) {
            this.applyRewardLine(rewardLine);
        }
        return true;
    },
    applyRewardLine(rewardLine) {
        const prepareRewards = {
            ...rewardLine,
            reward_id: rewardLine.reward_id,
            coupon_id: this.models["loyalty.card"].get(rewardLine.coupon_id),
            tax_ids: rewardLine.tax_ids.map((tax) => ["link", tax]),
        };
        this.models["pos.order.line"].create({
            ...prepareRewards,
            order_id: this,
            price_type: "manual",
        });
    },
    /**
     * Checks if there are any existing manual changes or new coupon additions for the given coupon code
     */
    duplicateCouponChanges(code) {
        return Object.keys(this.uiState.couponPointChanges).some((key) => {
            const change = this.uiState.couponPointChanges[key];
            return (
                (change.existing_code === code && change.manual) ||
                (change.code === code && change.coupon_id < 0)
            );
        });
    },
    /**
     * Processes a gift card by creating a new gift card.
     *
     * @param {String} newGiftCardCode gift card code as a string if new gift card to be created.
     * @param {number} points number of points to assign to the gift card.
     */
    processGiftCard(newGiftCardCode, points, expirationDate) {
        const partner_id = this.partner_id?.id || false;
        const product_id = this.getSelectedOrderline().product_id.id;
        const program =
            this.getSelectedOrderline()._e_wallet_program_id ||
            this.models["loyalty.program"].find((p) => p.program_type === "gift_card");

        let couponId;
        const couponData = {
            program_id: program?.id,
            points: points,
            manual: true,
            product_id: product_id,
        };

        // Fetch all coupon_ids for the specified points and not manually created, that are associated with the gift card program
        const applicableCouponIds = Object.keys(this.uiState.couponPointChanges).filter((key) => {
            const change = this.uiState.couponPointChanges[key];
            return (
                change.points === points &&
                change.program_id === program.id &&
                change.product_id === product_id &&
                !change.manual
            );
        });

        if (newGiftCardCode) {
            couponId = applicableCouponIds.shift() || loyaltyIdsGenerator();
            couponData.coupon_id = couponId;
            couponData.code = newGiftCardCode;
            couponData.partner_id = partner_id;
            couponData.expiration_date = expirationDate;
        }

        this.uiState.couponPointChanges[couponId] = couponData;
    },
    /**
     * @param {loyalty.reward} reward
     * @returns the discountable and discountable per tax for this discount on order reward.
     */
    _getDiscountableOnOrder(reward) {
        let discountable = 0;
        const discountablePerTax = {};
        for (const line of this.getOrderlines()) {
            if (!line.getQuantity()) {
                continue;
            }
            const taxKey = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
                ? line.tax_ids.map((t) => t.id)
                : line.tax_ids.filter((t) => t.amount_type !== "fixed").map((t) => t.id);
            discountable += line.prices.total_included;
            if (!discountablePerTax[taxKey]) {
                discountablePerTax[taxKey] = 0;
            }
            discountablePerTax[taxKey] += line.basePrice;
        }
        return { discountable, discountablePerTax };
    },
    /**
     * @param {loyalty.reward} reward
     * @returns the cheapest line from all the lines where the program is applicable
     */
    _getCheapestLine(reward) {
        const applicableProductIds = new Set(reward.all_discount_product_ids.map((p) => p.id));
        const filtered_lines = this.getOrderlines().filter(
            (line) =>
                !line.combo_parent_id &&
                !line.reward_id &&
                line.getQuantity() &&
                applicableProductIds.has(line.getProduct().id)
        );
        return filtered_lines.toSorted(
            (lineA, lineB) => lineA.comboTotalPrice / lineA.qty - lineB.comboTotalPrice / lineB.qty
        )[0];
    },
    /**
     * @returns the discountable and discountable per tax for this discount on cheapest reward.
     */
    _getDiscountableOnCheapest(reward) {
        const cheapestLine = this._getCheapestLine(reward);
        if (!cheapestLine) {
            return { discountable: 0, discountablePerTax: {} };
        }
        const taxKey = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
            ? cheapestLine.tax_ids.map((t) => t.id)
            : cheapestLine.tax_ids.filter((t) => t.amount_type !== "fixed").map((t) => t.id);
        return {
            discountable: cheapestLine.comboTotalBasePrice,
            discountablePerTax: Object.fromEntries([[taxKey, cheapestLine.comboTotalBasePrice]]),
        };
    },
    /**
     * @param {loyalty.reward} reward
     * @returns all lines to which the reward applies.
     */
    _getSpecificDiscountableLines(reward) {
        const discountableLines = [];
        const applicableProductIds = new Set(reward.all_discount_product_ids.map((p) => p.id));
        for (const line of this.getOrderlines()) {
            if (!line.getQuantity()) {
                continue;
            }
            if (
                applicableProductIds.has(line.getProduct().id) ||
                applicableProductIds.has(line._reward_product_id?.id)
            ) {
                discountableLines.push(line);
            }
        }
        return discountableLines;
    },
    /**
     * For a 'specific' type of discount it is more complicated as we have to make sure that we never
     *  discount more than what is available on a per line basis.
     * @param {loyalty.reward} reward
     * @returns the discountable and discountable per tax for this discount on specific reward.
     */
    _getDiscountableOnSpecific(reward) {
        const applicableProductIds = new Set(reward.all_discount_product_ids.map((p) => p.id));
        const linesToDiscount = [];
        const discountLinesPerReward = {};
        const orderLines = this.getOrderlines();
        const orderProducts = orderLines.map((line) => line.product_id.id);
        const remainingAmountPerLine = {};
        for (const line of orderLines) {
            if (!line.getQuantity() || !line.price_unit) {
                continue;
            }
            remainingAmountPerLine[line.uuid] = line.prices.total_included;
            const product_id = line.combo_parent_id?.product_id.id || line.getProduct().id;
            if (
                applicableProductIds.has(product_id) ||
                (line._reward_product_id && applicableProductIds.has(line._reward_product_id.id))
            ) {
                linesToDiscount.push(line);
            } else if (line.reward_id) {
                const lineReward = line.reward_id;
                const lineRewardApplicableProductsIds = new Set(
                    lineReward.all_discount_product_ids.map((p) => p.id)
                );
                if (
                    lineReward.id === reward.id ||
                    (orderProducts.some(
                        (product) =>
                            lineRewardApplicableProductsIds.has(product) &&
                            applicableProductIds.has(product)
                    ) &&
                        lineReward.reward_type === "discount" &&
                        lineReward.discount_mode != "percent")
                ) {
                    linesToDiscount.push(line);
                }
                if (!discountLinesPerReward[line.reward_identifier_code]) {
                    discountLinesPerReward[line.reward_identifier_code] = [];
                }
                discountLinesPerReward[line.reward_identifier_code].push(line);
            }
        }

        let cheapestLine = false;
        for (const lines of Object.values(discountLinesPerReward)) {
            const lineReward = lines[0].reward_id;
            if (lineReward.reward_type !== "discount") {
                continue;
            }
            let discountedLines = orderLines;
            if (lineReward.discount_applicability === "cheapest") {
                cheapestLine = cheapestLine || this._getCheapestLine(lineReward);
                discountedLines = [cheapestLine];
            } else if (lineReward.discount_applicability === "specific") {
                discountedLines = this._getSpecificDiscountableLines(lineReward);
            }
            if (!discountedLines.length) {
                continue;
            }
            if (lineReward.discount_mode === "percent") {
                const discount = lineReward.discount / 100;
                for (const line of discountedLines) {
                    if (line.reward_id) {
                        continue;
                    }
                    let discountedAmount = 0;
                    if (lineReward.discount_applicability === "cheapest") {
                        discountedAmount =
                            (-remainingAmountPerLine[line.uuid] * discount) / line.getQuantity();
                    } else {
                        discountedAmount = -remainingAmountPerLine[line.uuid] * discount;
                    }
                    if (lineReward.discount_max_amount && lineReward.discount_max_amount > 0) {
                        discountedAmount = Math.max(
                            discountedAmount,
                            -lineReward.discount_max_amount
                        );
                    }
                    remainingAmountPerLine[line.uuid] += discountedAmount;
                }
            }
        }

        let discountable = 0;
        const discountablePerTax = {};
        for (const line of linesToDiscount) {
            discountable += remainingAmountPerLine[line.uuid];
            const taxKey = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
                ? line.tax_ids.map((t) => t.id)
                : line.tax_ids.filter((t) => t.amount_type !== "fixed").map((t) => t.id);
            if (!discountablePerTax[taxKey]) {
                discountablePerTax[taxKey] = 0;
            }
            discountablePerTax[taxKey] +=
                line.basePrice * (remainingAmountPerLine[line.uuid] / line.prices.total_included);
        }
        return { discountable, discountablePerTax };
    },
    /**
     * @param {Object} args See `_applyReward`
     * @returns {Array} List of values to create the reward lines
     */
    _getRewardLineValues(args) {
        const reward = args["reward"];
        if (reward.reward_type === "discount") {
            return this._getRewardLineValuesDiscount(args);
        } else if (reward.reward_type === "product") {
            return this._getRewardLineValuesProduct(args);
        }
        // NOTE: we may reach this step if for some reason there is a free shipping reward
        return [];
    },
    /**
     * @param {Object} args See `_applyReward`
     * @returns {Array} List of values to create the discount lines
     */
    _getRewardLineValuesDiscount(args) {
        //LINK
        const reward = args["reward"];
        const coupon_id = args["coupon_id"];
        const rewardAppliesTo = reward.discount_applicability;
        let getDiscountable;
        if (rewardAppliesTo === "order") {
            getDiscountable = this._getDiscountableOnOrder.bind(this);
        } else if (rewardAppliesTo === "cheapest") {
            getDiscountable = this._getDiscountableOnCheapest.bind(this);
        } else if (rewardAppliesTo === "specific") {
            getDiscountable = this._getDiscountableOnSpecific.bind(this);
        }
        if (!getDiscountable) {
            return _t("Unknown discount type");
        }
        let { discountable, discountablePerTax } = getDiscountable(reward);
        // Other discounts may already cover part of the discountable lines
        const totalFactor = discountable > 0 ? Math.min(1, this.priceIncl / discountable) : 1;
        discountable = Math.min(this.priceIncl, discountable);
        if (floatIsZero(discountable)) {
            return [];
        }
        let maxDiscount = reward.discount_max_amount || Infinity;
        if (reward.discount_mode === "per_point") {
            // Rewards cannot be partially offered to customers
            const points = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
                ? this._getRealCouponPoints(coupon_id)
                : Math.floor(this._getRealCouponPoints(coupon_id) / reward.required_points) *
                  reward.required_points;
            maxDiscount = Math.min(maxDiscount, reward.discount * points);
        } else if (reward.discount_mode === "per_order") {
            maxDiscount = Math.min(maxDiscount, reward.discount);
        } else if (reward.discount_mode === "percent") {
            maxDiscount = Math.min(maxDiscount, discountable * (reward.discount / 100));
        }
        const rewardCode = _newRandomRewardCode();
        let pointCost = reward.clear_wallet
            ? this._getRealCouponPoints(coupon_id)
            : reward.required_points;
        if (reward.discount_mode === "per_point" && !reward.clear_wallet) {
            pointCost = Math.min(maxDiscount, discountable) / reward.discount;
        }
        // These are considered payments and do not require to be either taxed or split by tax
        const discountProduct = reward.discount_line_product_id;
        if (["ewallet", "gift_card"].includes(reward.program_id.program_type)) {
            const baseLine = discountProduct.getBaseLine({
                overridedValues: {
                    tax_ids: discountProduct.taxes_id,
                    price_unit: -Math.min(maxDiscount, discountable),
                    quantity: 1,
                    special_mode: "total_included",
                },
            });
            accountTaxHelpers.add_tax_details_in_base_line(baseLine, this.company);
            accountTaxHelpers.round_base_lines_tax_details([baseLine], this.company);
            accountTaxHelpers.fix_base_lines_tax_details_on_manual_tax_amounts(
                [baseLine],
                this.company
            );
            const extraTaxData = accountTaxHelpers.export_base_line_extra_tax_data(baseLine);

            return [
                {
                    product_id: discountProduct,
                    price_unit: baseLine.price_unit,
                    qty: 1,
                    reward_id: reward,
                    is_reward_line: true,
                    coupon_id: coupon_id,
                    points_cost: pointCost,
                    reward_identifier_code: rewardCode,
                    tax_ids: discountProduct.taxes_id,
                    extra_tax_data: extraTaxData,
                },
>>>>>>> 7e4f3ca701e5b61a140028970b5b7567d81cb645
            ];
        }
        this.applied_codes = [...this.applied_codes, appliedCode];

        if (card?.program_id && !card.program_id.is_payment_program) {
            this._autoClaimSingleProductReward(card.program_id);
        }
        return { success: true, program_id: program, rejection_message: "" };
    },
    /**
     * Claim a program's reward automatically when the program has a single reward.
     * @param {loyalty_program} program
     */
    _autoClaimSingleProductReward(program) {
        if (program.reward_ids.length !== 1) {
            return;
        }
        const reward = program.reward_ids[0];
        if (
            program.applies_on === "future" ||
            reward.reward_type !== "product" ||
            reward.multi_product
        ) {
            return;
        }
        this.active_rewards.push({ reward_id: reward.id });
    },
    /**
     * Funding an eWallet or selling/topping-up a gift card from a refund adds a positive
     * trigger-product line that offsets the refund and credits the card. That's the
     * intended way to "refund to an eWallet", not a new sale, so the refund guard must
     * not block it.
     */
    isSaleDisallowed(values, options) {
        const product = values.product_id || values.product_tmpl_id?.product_variant_ids?.[0];
        const isPaymentTrigger = this.models["loyalty.program"].some(
            (program) =>
                program.is_payment_program &&
                program.trigger_product_ids.some(
                    (triggerProduct) => triggerProduct.id === product?.id
                )
        );
        if (isPaymentTrigger) {
            return false;
        }
        return super.isSaleDisallowed(values, options);
    },
    _isItemCountExcludedLine(line) {
        return super._isItemCountExcludedLine(line) || line.is_reward_line;
    },

<<<<<<< 7434faa93558d4f46fdda77acd1be4dfc663ea7c
    /**
     * Gets the reward lines to be created for the reward and creates them  on the order
     * @param {loyalty_reward} reward
     * @param {number} points - the points available to spend on the reward
     * @param {object} opts - additional parameters. Here used to indicate for multi_product rewards
     *  which product use
     * @returns {object[]} the reward line value objects
     */
    applyReward(reward, points, opts) {
        const program = reward.program_id;
        const card =
            program &&
            this.models["loyalty.card"].find(
                (card) =>
                    card.program_id?.id === program.id && this.applied_codes.includes(card.code)
            );
        for (const values of reward.getRewardLines(this, points, opts)) {
            this.models["pos.order.line"].create({
                card_id: card || undefined,
                ...values,
                order_id: this,
||||||| 57fad2e46286b74d3832a3c7cea4a84327268224
            lst.push({
                product_id: discountProduct,
                price_unit: -(Math.min(this.priceIncl, entry[1]) * discountFactor),
                qty: 1,
                reward_id: reward,
                is_reward_line: true,
                coupon_id: coupon_id,
                points_cost: 0,
                reward_identifier_code: rewardCode,
                tax_ids: taxIds,
=======
            lst.push({
                product_id: discountProduct,
                price_unit: -(entry[1] * totalFactor * discountFactor),
                qty: 1,
                reward_id: reward,
                is_reward_line: true,
                coupon_id: coupon_id,
                points_cost: 0,
                reward_identifier_code: rewardCode,
                tax_ids: taxIds,
>>>>>>> 7e4f3ca701e5b61a140028970b5b7567d81cb645
            });
        }
    },
    /**
     * The tax-included price of a line still available to be discounted. Discounts applied earlier
     * in the current recompute pass record the reduced amount in _line_discountable_price; if the
     * line has not been discounted yet, its full price is returned.
     * @param {string} uuid - the (priced) order line uuid
     * @returns {number} the remaining discountable tax-included price
     */
    getLineDiscountablePrice(uuid) {
        if (uuid in this._line_discountable_price) {
            return this._line_discountable_price[uuid];
        }
        return this.models["pos.order.line"].getBy("uuid", uuid)?.priceIncl || 0;
    },
    /**
     * Removes the reward line from the order, calculates the available points on the program,
     * and then repplies the reward if possible
     */
    recomputeReward(reward, qty, reward_product_id) {
        const program = reward.program_id;
        if (!program) {
            return;
        }
        const points = program.getPoints(this);
        if (points < reward.required_points) {
            return;
        }
        this.applyReward(reward, points, { qty, reward_product_id });
    },
    /**
     * Recomputes the automatically applied rewards on the order. For every auto program, the
     * previously generated reward lines are dropped and, if the order now generates enough points,
     * rebuilt from the program's reward. Meant to be called whenever the order changes (a product
     * is added/removed or a quantity changes).
     */
    recomputeRewards() {
        if (this.finalized) {
            return;
        }
        // Guard against re-entrancy: creating/deleting reward lines must not trigger another pass.
        if (this._recomputingRewards) {
            return;
        }
        logPosMessage("PosOrder", "recomputeRewards", "Recomputing rewards");
        this._recomputingRewards = true;
        this._line_discountable_price = {};

        const selectedLine = this.getSelectedOrderline();
        const selectedRewardId = selectedLine?.is_reward_line ? selectedLine.reward_id?.id : null;
        try {
            for (const line of this.getOrderlines().filter((line) => line.is_reward_line)) {
                line.delete();
            }
            const activeRewardIds = new Set(this.active_rewards.map((entry) => entry.reward_id));

            // Within the auto programs, apply the discounts in the order sale_loyalty stacks
            // 'specific': cheapest, then order/global, then specific.
            const discountPrecedence = { cheapest: 0, order: 1, specific: 2 };
            const autoPrograms = this.appliedPrograms
                .filter((program) => !activeRewardIds.has(program.reward_ids[0].id))
                .sort(
                    (a, b) =>
                        (discountPrecedence[a.reward_ids[0].discount_applicability] ?? 3) -
                        (discountPrecedence[b.reward_ids[0].discount_applicability] ?? 3)
                );
            for (const program of autoPrograms) {
                this.recomputeReward(program.reward_ids[0]);
            }

            // Sort by qty so rewards with a user set qty are computed first before unset
            // qty rewards consume all the points
            const activeRewards = [...this.active_rewards].sort(
                (a, b) => (Number(a.qty) || Infinity) - (Number(b.qty) || Infinity)
            );
            for (const { reward_id, qty, reward_product_id } of activeRewards) {
                const reward = this.models["loyalty.reward"].get(reward_id);
                if (reward) {
                    this.recomputeReward(reward, qty, reward_product_id);
                }
            }

            const paymentPrograms = this.active_payment_programs.filter(
                (entry) =>
                    this.models["loyalty.reward"].get(entry.reward_id)?.discount_line_product_id
            );
            if (paymentPrograms.length !== this.active_payment_programs.length) {
                this.active_payment_programs = paymentPrograms;
            }
            for (const { reward_id, card_id, amount } of paymentPrograms) {
                this.applyPaymentProgram(
                    this.models["loyalty.reward"].get(reward_id),
                    this.models["loyalty.card"].get(card_id),
                    amount
                );
            }
        } finally {
            this._recomputingRewards = false;
        }
        if (selectedRewardId) {
            const rebuiltLine = this.getOrderlines().find(
                (line) => line.is_reward_line && line.reward_id?.id === selectedRewardId
            );
            if (rebuiltLine) {
                this.selectOrderline(rebuiltLine);
            }
        }
    },
    /**
     * Select the line a reward produced
     * Returns true if such a line exists (and was selected), false otherwise.
     */
    _selectRewardLine(reward) {
        const rewardLines = this.getOrderlines().filter(
            (line) => line.is_reward_line && line.reward_id?.id === reward.id
        );
        if (!rewardLines.length) {
            return false;
        }
        this.selectOrderline(rewardLines[rewardLines.length - 1]);
        return true;
    },
    /**
     * Drop every reward/program bound to a specific customer (nominative: loyalty &
     * eWallet). Called when the order's partner changes so rewards earned/spent by the
     * previous partner don't linger. Gift cards are code-based, not partner-bound, so
     * their payments are kept. The caller recomputes rewards afterwards, which only
     * rebuilds what the new partner is entitled to (nominative programs are never
     * auto-applied).
     */
    removeNominativeRewards() {
        for (const line of this.getOrderlines().filter((line) =>
            line.is_reward_line
                ? line.reward_id?.program_id?.is_nominative
                : line.payment_program_id?.is_nominative || line.card_id?.program_id?.is_nominative
        )) {
            line.delete();
        }
        this.active_rewards = this.active_rewards.filter(
            (entry) =>
                !this.models["loyalty.reward"].get(entry.reward_id)?.program_id?.is_nominative
        );
        this.active_payment_programs = this.active_payment_programs.filter(
            (entry) =>
                !this.models["loyalty.reward"].get(entry.reward_id)?.program_id?.is_nominative
        );
        this.applied_codes = this.applied_codes.filter((code) => {
            const card = this.models["loyalty.card"].find((card) => card.code === code);
            return !card?.program_id?.is_nominative;
        });
    },
    /**
     * Override removeOrderline to remove all lines which are linked to a
     * removed reward. Also will recompute auto rewards when a line is
     * removed
     */
    removeOrderline(lineToRemove) {
        if (lineToRemove.is_reward_line) {
            const reward = lineToRemove.reward_id;
            const card = lineToRemove.card_id;
            const linesToRemove = this.getOrderlines().filter(
                (line) => line.reward_id === reward && (!card || line.card_id === card)
            );
            const removedCodes = new Set(
                linesToRemove.map((line) => line.card_id?.code).filter(Boolean)
            );
            // Deleting a line emits no event the fee listens to.
            const feeBaseChanged = linesToRemove.some((line) => line.isServiceFeeApplicable());
            for (const line of linesToRemove) {
                line.delete();
            }
            if (feeBaseChanged) {
                this.recomputeServiceFees();
            }

            this.applied_codes = this.applied_codes.filter((code) => !removedCodes.has(code));
            this.active_rewards = this.active_rewards.filter(
                (entry) => entry.reward_id !== reward?.id
            );
            this.active_payment_programs = this.active_payment_programs.filter(
                (entry) => entry.reward_id !== reward?.id || (card && entry.card_id !== card.id)
            );
            const programId = reward?.program_id?.id;
            if (programId && !this.disabled_program_ids.includes(programId)) {
                this.disabled_program_ids = [...this.disabled_program_ids, programId];
            }
            this.recomputeRewards();

            this.selectOrderline(this.getLastOrderline());
            return true;
        }
        const result = super.removeOrderline(lineToRemove);
        this.recomputeRewards();
        return result;
    },
});
