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
<<<<<<< 410961c4839d6fa2864245c4b1862e593e9f895b
        const appliedCode = rule ? rule.code : code;
        if (this.applied_codes.includes(appliedCode)) {
            return {
                success: false,
                program_id: null,
                rejection_message: _t("That card code has already been scanned and activated."),
            };
||||||| 31cb034a88ca322cff26e51feba1a4c4a147c9cc
        return Object.entries(loyaltyPoints).map(([couponId, points]) => ({
            couponId,
            points,
            program: points.program,
        }));
    },
    /**
     * The points in the couponPointChanges for free product reward is not correct.
     * It doesn't take into account the points from the `free` product. Use this method
     * to compute the necessary correction.
     * @param {*} program
     * @returns {number}
     */
    _getPointsCorrection(program) {
        const rewardLines = this.lines.filter((line) => line.is_reward_line);
        if (!this._canGenerateRewards(program, this.priceIncl, this.priceExcl)) {
            return 0;
=======
        return Object.entries(loyaltyPoints).map(([couponId, points]) => ({
            couponId,
            points,
            program: points.program,
        }));
    },
    /**
     * The points in the couponPointChanges for free product reward is not correct.
     * It doesn't take into account the points from the `free` product. Use this method
     * to compute the necessary correction.
     * @param {*} program
     * @returns {number}
     */
    _getPointsCorrection(program) {
        return this._getPointsCorrectionForLines(
            program,
            this.lines.filter((line) => line.is_reward_line)
        );
    },
    _getPointsCorrectionForLines(program, rewardLines) {
        if (!this._canGenerateRewards(program, this.priceIncl, this.priceExcl)) {
            return 0;
>>>>>>> 699179e04afb597e3b27f5fb5c3b6187f4d8f4b6
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

        if (card?.program_id?.is_payment_program) {
            this.active_payment_programs = [
                ...this.active_payment_programs,
                { reward_id: card.program_id.reward_ids[0].id, card_id: card.id },
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
<<<<<<< 410961c4839d6fa2864245c4b1862e593e9f895b
    getLineDiscountablePrice(uuid) {
        if (uuid in this._line_discountable_price) {
            return this._line_discountable_price[uuid];
||||||| 31cb034a88ca322cff26e51feba1a4c4a147c9cc
    _computeUnclaimedFreeProductQty(reward, coupon_id, product, remainingPoints) {
        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        let claimed = 0;
        let available = 0;
        let shouldCorrectRemainingPoints = false;
        for (const line of this.getOrderlines()) {
            if (
                reward.reward_product_ids.map((reward) => reward.id).includes(product.id) &&
                reward.reward_product_ids.map((reward) => reward.id).includes(line.getProduct().id)
            ) {
                if (this._get_reward_lines() == 0) {
                    if (line.getProduct() === product) {
                        available += line.getQuantity();
                    }
                } else {
                    available += line.getQuantity();
                }
            } else if (
                reward.reward_product_ids
                    .map((reward) => reward.id)
                    .includes(line._reward_product_id?.id)
            ) {
                if (line.reward_id.id == reward.id) {
                    remainingPoints += line.points_cost;
                    claimed += line.getQuantity();
                } else {
                    shouldCorrectRemainingPoints = true;
                }
            }
=======
    _computeUnclaimedFreeProductQty(reward, coupon_id, product, remainingPoints) {
        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        let claimed = 0;
        let available = 0;
        for (const line of this.getOrderlines()) {
            if (
                reward.reward_product_ids.map((reward) => reward.id).includes(product.id) &&
                reward.reward_product_ids.map((reward) => reward.id).includes(line.getProduct().id)
            ) {
                if (this._get_reward_lines() == 0) {
                    if (line.getProduct() === product) {
                        available += line.getQuantity();
                    }
                } else {
                    available += line.getQuantity();
                }
            } else if (
                reward.reward_product_ids
                    .map((reward) => reward.id)
                    .includes(line._reward_product_id?.id)
            ) {
                if (line.reward_id.id == reward.id) {
                    remainingPoints += line.points_cost;
                    claimed += line.getQuantity();
                }
            }
>>>>>>> 699179e04afb597e3b27f5fb5c3b6187f4d8f4b6
        }
<<<<<<< 410961c4839d6fa2864245c4b1862e593e9f895b
        return this.models["pos.order.line"].getBy("uuid", uuid)?.priceIncl || 0;
||||||| 31cb034a88ca322cff26e51feba1a4c4a147c9cc
        let freeQty;
        if (reward.program_id.trigger == "auto") {
            if (
                this._isRewardProductPartOfRules(reward, product) &&
                reward.program_id.applies_on !== "future"
            ) {
                // OPTIMIZATION: Pre-calculate the factors for each reward-product combination during the loading.
                // For points not based on quantity, need to normalize the points to compute free quantity.
                const appliedRulesIds = this.uiState.couponPointChanges[coupon_id].appliedRules;
                const appliedRules =
                    appliedRulesIds !== undefined
                        ? reward.program_id.rule_ids.filter((rule) =>
                              appliedRulesIds.includes(rule.id)
                          )
                        : reward.program_id.rule_ids;
                let factor = 0;
                let orderPoints = 0;
                for (const rule of appliedRules) {
                    if (rule.any_product || rule.validProductIds.has(product.id)) {
                        if (rule.reward_point_mode === "order") {
                            orderPoints += rule.reward_point_amount;
                        } else if (rule.reward_point_mode === "money") {
                            factor += ProductPrice.round(
                                rule.reward_point_amount * product.lst_price
                            );
                        } else if (rule.reward_point_mode === "unit") {
                            factor += rule.reward_point_amount;
                        }
                    }
                }
                if (factor === 0) {
                    freeQty = Math.floor(
                        (remainingPoints / reward.required_points) * reward.reward_product_qty
                    );
                } else {
                    const correction = shouldCorrectRemainingPoints
                        ? this._getPointsCorrection(reward.program_id)
                        : 0;
                    freeQty = computeFreeQuantity(
                        (remainingPoints - correction - orderPoints) / factor,
                        reward.required_points / factor,
                        reward.reward_product_qty
                    );
                    freeQty += Math.floor(
                        (orderPoints / reward.required_points) * reward.reward_product_qty
                    );
                }
            } else {
                freeQty = Math.floor(
                    (remainingPoints / reward.required_points) * reward.reward_product_qty
                );
            }
        } else if (reward.program_id.trigger == "with_code") {
            freeQty = Math.floor(
                (remainingPoints / reward.required_points) * reward.reward_product_qty
            );
        }
        return Math.min(available, freeQty) - claimed;
    },
    _computePotentialFreeProductQty(reward, product, remainingPoints) {
        if (reward.program_id.trigger == "auto") {
            if (
                this._isRewardProductPartOfRules(reward, product) &&
                reward.program_id.applies_on !== "future"
            ) {
                // Compute the correction points once even if there are multiple reward lines.
                // This is because _getPointsCorrection is taking into account all the lines already.
                const claimedPoints = this._getPointsCorrection(reward.program_id);
                return Math.floor((remainingPoints - claimedPoints) / reward.required_points) > 0
                    ? reward.reward_product_qty
                    : 0;
            } else {
                return Math.floor(
                    (remainingPoints / reward.required_points) * reward.reward_product_qty
                );
            }
        } else if (reward.program_id.trigger == "with_code") {
            return Math.floor(
                (remainingPoints / reward.required_points) * reward.reward_product_qty
            );
        }
    },
    _getRewardedProduct(reward, args) {
        return (
            reward.reward_product_ids.find((p) => p.id === args["product"]?.id) ||
            reward.reward_product_ids[0]
        );
=======
        let freeQty;
        if (reward.program_id.trigger == "auto") {
            if (
                this._isRewardProductPartOfRules(reward, product) &&
                reward.program_id.applies_on !== "future"
            ) {
                // OPTIMIZATION: Pre-calculate the factors for each reward-product combination during the loading.
                // For points not based on quantity, need to normalize the points to compute free quantity.
                const appliedRulesIds = this.uiState.couponPointChanges[coupon_id].appliedRules;
                const appliedRules =
                    appliedRulesIds !== undefined
                        ? reward.program_id.rule_ids.filter((rule) =>
                              appliedRulesIds.includes(rule.id)
                          )
                        : reward.program_id.rule_ids;
                let factor = 0;
                let orderPoints = 0;
                for (const rule of appliedRules) {
                    if (rule.any_product || rule.validProductIds.has(product.id)) {
                        if (rule.reward_point_mode === "order") {
                            orderPoints += rule.reward_point_amount;
                        } else if (rule.reward_point_mode === "money") {
                            factor += ProductPrice.round(
                                rule.reward_point_amount * product.lst_price
                            );
                        } else if (rule.reward_point_mode === "unit") {
                            factor += rule.reward_point_amount;
                        }
                    }
                }
                if (factor === 0) {
                    freeQty = Math.floor(
                        (remainingPoints / reward.required_points) * reward.reward_product_qty
                    );
                } else {
                    const correction = this._getPointsCorrectionForLines(
                        reward.program_id,
                        this._get_reward_lines().filter((line) => line.reward_id.id !== reward.id)
                    );
                    freeQty = computeFreeQuantity(
                        (remainingPoints - correction - orderPoints) / factor,
                        reward.required_points / factor,
                        reward.reward_product_qty
                    );
                    freeQty += Math.floor(
                        (orderPoints / reward.required_points) * reward.reward_product_qty
                    );
                }
            } else {
                freeQty = Math.floor(
                    (remainingPoints / reward.required_points) * reward.reward_product_qty
                );
            }
        } else if (reward.program_id.trigger == "with_code") {
            freeQty = Math.floor(
                (remainingPoints / reward.required_points) * reward.reward_product_qty
            );
        }
        return Math.min(available, freeQty) - claimed;
    },
    _computePotentialFreeProductQty(reward, product, remainingPoints) {
        if (reward.program_id.trigger == "auto") {
            if (
                this._isRewardProductPartOfRules(reward, product) &&
                reward.program_id.applies_on !== "future"
            ) {
                // Compute the correction points once even if there are multiple reward lines.
                // This is because _getPointsCorrection is taking into account all the lines already.
                const claimedPoints = this._getPointsCorrection(reward.program_id);
                return Math.floor((remainingPoints - claimedPoints) / reward.required_points) > 0
                    ? reward.reward_product_qty
                    : 0;
            } else {
                return Math.floor(
                    (remainingPoints / reward.required_points) * reward.reward_product_qty
                );
            }
        } else if (reward.program_id.trigger == "with_code") {
            return Math.floor(
                (remainingPoints / reward.required_points) * reward.reward_product_qty
            );
        }
    },
    _getRewardedProduct(reward, args) {
        return (
            reward.reward_product_ids.find((p) => p.id === args["product"]?.id) ||
            reward.reward_product_ids[0]
        );
>>>>>>> 699179e04afb597e3b27f5fb5c3b6187f4d8f4b6
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
