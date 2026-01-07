import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { SelectRewardPopup } from "@pos_self_order_loyalty/app/components/popup/select_reward_popup/select_reward_popup";
import { SelectProductPopup } from "@pos_self_order_loyalty/app/components/popup/select_product_popup/select_product_popup";
import { _newRandomRewardCode } from "@pos_loyalty/app/models/pos_order";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(SelfOrder.prototype, {
    //#region Overrides
    async setup(env, services) {
        await super.setup(...arguments);
        // this.deleteUnrelatedLoyaltyCards();
    },
    createNewOrder() {
        const order = super.createNewOrder();
        this.deleteUnrelatedLoyaltyCards();
        if (this.config.self_ordering_mode == "mobile") {
            const partner = this.models["res.partner"].getFirst();
            if (partner) {
                order.setPartner(partner);
            }
        }
        return order;
    },
    async initMobileData() {
        // If we load an existing order with synced reward lines, they will be updated. If we load an existing order without
        // synced reward lines. If we keep them, we can create duplicate reward lines when loading an existing order.
        this.models["pos.order.line"].filter((line) => line.is_reward_line && !line.isSynced).forEach((line) => {
            line.delete();
        });
        return super.initMobileData(...arguments);
    },
    async addToCart(
        productTemplate,
        qty,
        customer_note,
        selectedValues = {},
        customValues = {},
        comboValues = {},
        opts = {},
        uiState = {}
    ) {
        await super.addToCart(...arguments);
        await this.updateProgramsAndRewards();
    },
    async sendDraftOrderToServer() {
        const dirtyLoyaltyCards = this.models["loyalty.card"].filter((card) => card.isDirty())
        if (dirtyLoyaltyCards.length === 0) {
            return super.sendDraftOrderToServer(...arguments);
        }
        const serializedCards = [];
        for (const card of dirtyLoyaltyCards) {
            serializedCards.push(card.serializeForORM());
        }
        const data = await rpc(
            `/pos-self-order/process-loyalty-cards/`,
            {
                access_token: this.access_token,
                serialized_cards: serializedCards,
            }
        );
        this.models.connectNewData(data);
        return super.sendDraftOrderToServer(...arguments);
    },
    //#region Barcode Methods
    async _barcodePartnerAction(code) {
        if (!this.ordering) {
            return;
        }
        if (this.config.self_ordering_mode == "mobile" && this.currentOrder.getPartner()) {
            return;
        }
        // No need to check the local data, we always want to be up to date so we query the backend
        let partner = null;
        try {
            const data = await rpc(`/pos-self-order/get-partner-by-barcode/`, {
                access_token: this.access_token,
                partner_barcode: code.code,
            });
            const result = this.models.connectNewData(data);
            if (this.config.self_ordering_mode == "mobile") {
                this.data.debouncedSynchronizeLocalDataInIndexedDB();
            }
            partner = result['res.partner'].length > 0 && result['res.partner'][0];
        } catch (error) {
            this.handleErrorNotification(error);
            return;
        }
        if (!partner) {
            this.notification.add(_t("Customer not found"), {
                type: "danger",
            });
            return;
        }
        if (this.currentOrder.getPartner() !== partner) {
            this.currentOrder.setPartner(partner);
            await this.updateProgramsAndRewards();
            this.notification.add(_t("Welcome back %s", partner.name), {
                type: "success",
            });
            this.dialog.closeAll();
        }
    },
    async _barcodeCouponCodeAction(code) {
        if (!this.ordering) {
            return;
        }
        this.dialog.closeAll();
        await this.applyCouponCode(code.code);
    },

    //#region Loyalty programs handling
    getLoyaltyCards() {
        const partner = this.currentOrder.getPartner();
        if (!partner) {
            return [];
        }
        const loyaltyCards = this.models["loyalty.card"].filter((card) => card.partner_id?.id === partner?.id && card.program_id.program_type === "loyalty");
        return loyaltyCards;
    },
    getLoyaltyPrograms(rewardType = false, claimableOnly = false) {
        return this.getProgram(['loyalty'], rewardType, claimableOnly);
    },
    getPromotionPrograms(claimableOnly = false) {
        return this.getProgram(['promotion', 'buy_x_get_y'], false, claimableOnly);
    },
    getProgram(programType = [], rewardType = false, claimableOnly = false) {
        const loyalty_programs = this.models["loyalty.program"].filter((program) => programType.includes(program.program_type));
        const loyaltyPrograms = {};
        for (const program of loyalty_programs) {
            loyaltyPrograms[program.id] = program.reward_ids;
            if (rewardType) {
                loyaltyPrograms[program.id] = loyaltyPrograms[program.id].filter((reward) => reward.reward_type === rewardType)
            }
            if (claimableOnly) {
                loyaltyPrograms[program.id] = loyaltyPrograms[program.id].filter((reward) => this.getLoyaltyPoints(program) >= reward.required_points)
            }
            if (loyaltyPrograms[program.id].length === 0) {
                delete loyaltyPrograms[program.id];
            }
        }
        return loyaltyPrograms;
    },
    getLoyaltyPoints(program) {
        return (program.uiState.linkedCard?.points || 0) + program.uiState.pointsDifference;
    },
    getProgramPointsString(program, withPointName = true) {
        const points = Math.round(this.getLoyaltyPoints(program) * 100) / 100;
        return withPointName ? `${points} ${program.portal_point_name}` : points.toString();
    },
    getMaximumReedemablePoints(card, reward) {
        if (!card) {
            return 0;
        }
        const order = this.currentOrder;
        const maxOrderPoints = order.priceIncl / reward.required_points;
        const maxCardPoints = card.points;
        return Math.min(maxOrderPoints, maxCardPoints);
    },
    getClaimableRewards(card) {
        if (!card) {
            return;
        }
        const potentialRewards = card.program_id.reward_ids;
        const points = card.points;
        return potentialRewards.filter((reward) => points >= reward.required_points);
    },
    deleteUnrelatedLoyaltyCards() {
        // Theses cards can either be found again by a request to the server, either be recreated if needed by the js.
        const cardsToRemove = this.models["loyalty.card"].filter((card) => ["coupon", "promo_code", "gift_card", "promotion", "buy_x_get_y", "next_order_coupon"].includes(card.program_id.program_type));
        // Remove all programs and related stuff linked to codes
        const programToRemove = this.models["loyalty.program"].filter((program) => ["coupon", "promo_code", "gift_card", "next_order_coupon"].includes(program.program_type));
        const programToRemoveIds = programToRemove.map((p) => p.id);
        const rulesToRemove = this.models["loyalty.rule"].filter((rule) => programToRemoveIds.includes(rule.program_id.id));
        const rewardToRemove = this.models["loyalty.reward"].filter((reward) => programToRemoveIds.includes(reward.program_id.id));
        this.models["loyalty.card"].deleteMany(cardsToRemove);
        this.models["loyalty.program"].deleteMany(programToRemove);
        this.models["loyalty.rule"].deleteMany(rulesToRemove);
        this.models["loyalty.reward"].deleteMany(rewardToRemove);
        this.models["loyalty.reward"].forEach((reward) => reward.uiState.proposedToUser = false);
    },
    //#region Reward application
    applyReward(reward, card, code = "", opts = {}) {
        if (!reward) {
            return;
        }
        if (!card) {
            card = reward.program_id.uiState.linkedCard;
        }
        if (reward.reward_type === "product") {
            this.applyRewardProduct(reward, card, code);
        } else if (reward.reward_type === "discount") {
            this.applyRewardDiscount(reward, card, code);
        }
    },
    applyRewardProduct(reward, card, code = "") {
        // Can be multiple products
        const product = reward.reward_product_ids;
        const rewardOpts = { reward_id: reward.id, card_id: card.id };
        if (code) {
            rewardOpts.code = code;
        }
        if (product.length == 1) {
            this.selectProduct(product[0].product_tmpl_id, () => {}, rewardOpts);
            return;
        }
        if (product.every((p) => p.product_tmpl_id.id === product[0].product_tmpl_id.id)) {
            this.selectProduct(product[0].product_tmpl_id, () => {}, rewardOpts);
            return;
        }
        this.dialog.add(SelectProductPopup, {
            products: new Set(product.map((p) => p.product_tmpl_id)),
            getPayload: (productTemplate) => this.selectProduct(productTemplate, () => {}, rewardOpts),
        })
        return;
    },
    applyRewardDiscount(reward, card, code = "") {
        // Can be discount in %, $ or $ per point
        // Each can be on Order, cheapest product or specific product
        const rewardOpts = this.getRewardOpts(reward, card);        
        const product = reward.discount_line_product_id;
        const discountPerTax = this.currentOrder.computeDiscountAmount(reward, rewardOpts.points_cost);

        const points_cost = rewardOpts.points_cost;
        delete rewardOpts.points_cost;
        if (discountPerTax.length !== 0) {
            discountPerTax[0].points_cost = points_cost;
        }

        for (const discount of discountPerTax) {
            const newLine = this.models["pos.order.line"].create({
                order_id: this.currentOrder,
                product_id: product,
                qty: 1,
                note: "",
                price_extra: 0,
                price_type: "original",
                ...discount,
                ...rewardOpts,
            });
            if (code) {
                newLine.uiState.rewardCode = code;
            }
        }
    },
    async applyRewardFromCard(card, code = "") {
        if (!card) {
            return;
        }
        const rewards = this.getClaimableRewards(card);
        if (["ewallet", "gift_card"].includes(card.program_id.program_type)){
            const reward = rewards[0];
            const rewardOpts = this.getRewardOpts(reward, card);
            const points_cost = this.getMaximumReedemablePoints(card, reward);
            rewardOpts.points_cost = points_cost;
            rewardOpts.price_unit = this.currency.round(-points_cost * reward.required_points);
            const product = reward.discount_line_product_id;
            const newLine = this.models["pos.order.line"].create({
                order_id: this.currentOrder,
                product_id: product,
                qty: 1,
                note: _t("Gift Card"),
                price_extra: 0,
                price_type: "original",
                ...rewardOpts,
            });
            newLine.uiState.rewardCode = code;
            if (this.router.activeSlot == "payment") {
                const order = await this.sendDraftOrderToServer();
                if (this.currency.isZero(order.priceIncl)) {
                    await this.confirmationPage("order", this.config.self_ordering_mode, order.access_token);
                }
            }
        } else if (this.router.activeSlot == "cart") {
            if (!rewards || rewards.length == 0) {
                return;
            }
            if (rewards.length > 1) {
                //ask user which reward he wants to apply.
                this.dialog.add(SelectRewardPopup, {
                    rewards: rewards,
                    getPayload: (reward) => this.applyReward(reward, card, code),
                });
            } else {
                this.applyReward(rewards[0], card, code);
            }
        }
    },
    applyRewardFromReward(reward) {
        if (!reward) {
            return;
        }
        const program = reward.program_id;
        const partner = this.currentOrder.getPartner();
        let loyaltyCards = this.models["loyalty.card"].filter((card) => card.program_id.id == program.id && !card.isExpired());
        if (program.is_nominative) {
            if (!partner) {
                this.notification.add(_t("Please identify yourself to claim this reward."), {
                    type: "warning",
                });
                return;
            }
            loyaltyCards = loyaltyCards.filter((card) => card.partner_id && card.partner_id.id == partner.id);
        }
        if (loyaltyCards.length == 0) {
            this.notification.add(_t("No loyalty card available to claim this reward."), {
                type: "warning",
            });
            return;
        }
        // Take loyalty card with most points
        loyaltyCards = loyaltyCards.reduce((maxCard, card) => card.points > maxCard.points ? card : maxCard, loyaltyCards[0]);
        this.applyReward(reward, loyaltyCards);
    },
    async applyCouponCode(coupon_code) {
        const data = await rpc(`/pos-self-order/check-coupon-code/`, {
            access_token: this.access_token,
            coupon_code: coupon_code,
            partner_id: this.currentOrder.getPartner()?.id || null,
            order_uuid: this.currentOrder.uuid,
        });
        const result = this.models.connectNewData(data);
        if (result['loyalty.card'].length == 0) {
            this.notification.add(_t("Invalid coupon code"), {
                type: "warning",
            });
            return;
        }
        for (const card of result['loyalty.card']) {
            await this.applyRewardFromCard(card, coupon_code);
        }
    },
    getRewardOpts(reward_id, card_id) {
        const rewardOpts = {
            is_reward_line: true,
            reward_id: reward_id,
            coupon_id: card_id,
            reward_identifier_code: _newRandomRewardCode(),
            points_cost: reward_id.clear_wallet ? card_id.points : reward_id.required_points,
            price_type: "automatic",
        };
        if (reward_id.reward_type === "product") {
            rewardOpts.price_unit = 0;
            rewardOpts.qty = reward_id.reward_product_qty;
        }
        return rewardOpts;
    },
    addToOrderOpts(opts) {
        let props = super.addToOrderOpts(opts);
        if (opts.reward_id && opts.card_id) {
            props = {
                ...props,
                ...this.getRewardOpts(this.models["loyalty.reward"].get(opts.reward_id), this.models["loyalty.card"].get(opts.card_id)),
            };
        }
        return props;
    },
    addToOrderUiState(opts) {
        let uiState = super.addToOrderUiState(opts);
        if (opts.code) {
            uiState = {
                ...uiState,
                rewardCode: opts.code,
            }
        }
        return uiState;
    },
    //#region Update programs
    async updateProgramsAndRewards() {
        // Update loyalty points
        this.currentOrder.updateLoyaltyPoints();

        // Update rewards

        this.checkRemovableRewards();
        // Check promotions
        await this.applyPromotions();
        await this.updateDiscountReward();
    },
    async applyPromotions() {
        const applicablePromotions = this.checkPromotions();
        if (applicablePromotions.length > 0) {
            const reward = await makeAwaitable(this.dialog, SelectRewardPopup, {
                title: _t("You have promotions available!"),
                showDivisions: false,
                rewards: applicablePromotions,
            });
            if (!reward) {
                applicablePromotions.forEach((r) => { r.uiState.proposedToUser = true; });
                return;
            }
            this.applyReward(reward, null);
        }
    },
    checkPromotions() {
        const promotions = this.getPromotionPrograms();
        const applicablePromotions = [];
        for (const programId in promotions) {
            const program = this.models["loyalty.program"].get(programId);
            if (this.getLoyaltyPoints(program) <= 0) {
                continue;
            }
            for (const reward of promotions[programId]) {
                if (this.getLoyaltyPoints(program) >= reward.required_points) {
                    if (reward.uiState.proposedToUser) {
                        continue;
                    }
                    applicablePromotions.push(reward);
                }
            }
        }
        return applicablePromotions;
    },
    checkRemovableRewards() {
        const toRemove = [];
        const seenRewards = new Set();
        const rewardLines = this.currentOrder.lines.filter((line) => line.is_reward_line && ["promotion", "buy_x_get_y", "loyalty"].includes(line.reward_id.program_id.program_type))
        const pointsPerReward = rewardLines.reduce((acc, line) => {
            acc[line.reward_identifier_code] = (acc[line.reward_identifier_code] || 0) +  line.points_cost;
            return acc;
        }, {});
        const programPointsUsed = {};
        for (const line of rewardLines) {
            if (seenRewards.has(line.reward_identifier_code)) {
                continue;
            }
            seenRewards.add(line.reward_identifier_code);
            const pointsCost = pointsPerReward[line.reward_identifier_code];
            const program = line.reward_id.program_id;
            const programPoints = this.getLoyaltyPoints(program);
            if (programPoints + (programPointsUsed[program.id] || 0) < 0) {
                toRemove.push(line.reward_identifier_code);
                programPointsUsed[program.id] = (programPointsUsed[program.id] || 0) + pointsCost;
            }
        }
        const linesToRemove = this.currentOrder.lines.filter((line) => line.is_reward_line && toRemove.includes(line.reward_identifier_code));
        for (const line of linesToRemove) {
            line.delete();
        }
        this.currentOrder.updateAppliedCouponCodes();
    },
    async updateDiscountReward() {
        // Remove existing discount and re-apply them
        const rewardsToCheck = [];
        const linesToRemove = new Set();
        for (const line of this.currentOrder.lines) {
            if (!linesToRemove.has(line) && line.is_reward_line && line.reward_id.reward_type === 'discount') {
                const relatedLines = this.currentOrder.lines.filter(l => l.is_reward_line && l.reward_identifier_code === line.reward_identifier_code);
                rewardsToCheck.push([line.reward_id, line.coupon_id, line.uiState.rewardCode]);
                relatedLines.forEach(l => {
                    linesToRemove.add(l);
                });
            }
        }
        for (const line of linesToRemove) {
            line.delete();
        }
        for (const [reward, card, code] of rewardsToCheck) {
            if (["ewallet", "gift_card"].includes(card.program_id.program_type)) {
                await this.applyRewardFromCard(card, code);
            } else {
                this.applyRewardDiscount(reward, card, code);
            }
        }
    },   
});
