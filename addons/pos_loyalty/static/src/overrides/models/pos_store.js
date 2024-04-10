/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { Domain, InvalidDomainError } from "@web/core/domain";
import { ask, makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { Mutex } from "@web/core/utils/concurrency";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";

let nextId = -1;
const mutex = new Mutex();
const updateRewardsMutex = new Mutex();
const pointsForProgramsCountedRules = {};
const { DateTime } = luxon;

export function loyaltyIdsGenerator() {
    return nextId--;
}

function inverted(fn) {
    return (arg) => !fn(arg);
}

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);

        this.couponByLineUuidCache = {};
        this.rewardProductByLineUuidCache = {};

        effect(
            batched((orders) => {
                const order = Object.values(orders).find(
                    (order) => order.uuid === this.selectedOrderUuid
                );

                if (order) {
                    this.updateOrder(order);
                }
            }),
            [this.data.records["pos.order"]]
        );
    },
    async updateOrder(order) {
        // Read value to trigger effect
        order?.lines?.length;
        await this.orderUpdateLoyaltyPrograms();
    },
    async selectPartner(partner) {
        await super.selectPartner(partner);
        await this.updateRewards();
    },
    async selectPricelist(pricelist) {
        await super.selectPricelist(pricelist);
        await this.updateRewards();
    },
    async resetPrograms() {
        const order = this.get_order();
        order._resetPrograms();
        await this.orderUpdateLoyaltyPrograms();
        await this.updateRewards();
    },
    async orderUpdateLoyaltyPrograms() {
        if (!this.get_order()) {
            return;
        }

        await this.checkMissingCoupons();
        await this.updatePrograms();
    },
    updateRewards() {
        // Calls are not expected to take some time besides on the first load + when loyalty programs are made applicable
        if (this.models["loyalty.program"].length === 0) {
            return;
        }

        const order = this.get_order();
        updateRewardsMutex.exec(() => {
            return this.orderUpdateLoyaltyPrograms().then(async () => {
                // Try auto claiming rewards
                const claimableRewards = order.getClaimableRewards(false, false, true);
                let changed = false;
                for (const { coupon_id, reward } of claimableRewards) {
                    if (
                        reward.program_id.reward_ids.length === 1 &&
                        !reward.program_id.is_nominative &&
                        (reward.reward_type !== "product" ||
                            (reward.reward_type == "product" && !reward.multi_product))
                    ) {
                        order._applyReward(reward, coupon_id);
                        changed = true;
                    }
                }
                // Rewards may impact the number of points gained
                if (changed) {
                    await this.orderUpdateLoyaltyPrograms();
                }
                order._updateRewardLines();
            });
        });
    },
    async couponForProgram(program) {
        const order = this.get_order();
        if (program.is_nominative) {
            return this.fetchLoyaltyCard(program.id, order.get_partner().id);
        }
        // This type of coupons don't need to really exist up until validating the order, so no need to cache
        return this.models["loyalty.card"].create({
            id: loyaltyIdsGenerator(),
            code: null,
            program_id: program,
            partner_id: order.partner_id,
            points: 0,
        });
    },
    /**
     * Update our couponPointChanges, meaning the points/coupons each program give etc.
     */
    async updatePrograms() {
        const order = this.get_order();
        if (!order) {
            return;
        }
        const changesPerProgram = {};
        const programsToCheck = new Set();
        // By default include all programs that are considered 'applicable'
        for (const program of this.models["loyalty.program"].getAll()) {
            if (order._programIsApplicable(program)) {
                programsToCheck.add(program.id);
            }
        }
        for (const pe of Object.values(order.uiState.couponPointChanges)) {
            if (!changesPerProgram[pe.program_id]) {
                changesPerProgram[pe.program_id] = [];
                programsToCheck.add(pe.program_id);
            }
            changesPerProgram[pe.program_id].push(pe);
        }
        for (const coupon of order.code_activated_coupon_ids) {
            programsToCheck.add(coupon.program_id.id);
        }
        const programs = [...programsToCheck].map((programId) =>
            this.models["loyalty.program"].get(programId)
        );
        const pointsAddedPerProgram = order.pointsForPrograms(programs);
        for (const program of this.models["loyalty.program"].getAll()) {
            // Future programs may split their points per unit paid (gift cards for example), consider a non applicable program to give no points
            const pointsAdded = order._programIsApplicable(program)
                ? pointsAddedPerProgram[program.id]
                : [];
            // For programs that apply to both (loyalty) we always add a change of 0 points, if there is none, since it makes it easier to
            //  track for claimable rewards, and makes sure to load the partner's loyalty card.
            if (program.is_nominative && !pointsAdded.length && order.get_partner()) {
                pointsAdded.push({ points: 0 });
            }
            const oldChanges = changesPerProgram[program.id] || [];
            // Update point changes for those that exist
            for (let idx = 0; idx < Math.min(pointsAdded.length, oldChanges.length); idx++) {
                Object.assign(oldChanges[idx], pointsAdded[idx]);
            }
            if (pointsAdded.length < oldChanges.length) {
                const removedIds = oldChanges.map((pe) => pe.coupon_id);
                order.uiState.couponPointChanges = Object.fromEntries(
                    Object.entries(order.uiState.couponPointChanges).filter(([k, pe]) => {
                        return !removedIds.includes(pe.coupon_id);
                    })
                );
            } else if (pointsAdded.length > oldChanges.length) {
                for (const pa of pointsAdded.splice(oldChanges.length)) {
                    const coupon = await this.couponForProgram(program);
                    order.uiState.couponPointChanges[coupon.id] = {
                        points: pa.points,
                        program_id: program.id,
                        coupon_id: coupon.id,
                        barcode: pa.barcode,
                        appliedRules: pointsForProgramsCountedRules[program.id],
                    };
                }
            }
        }

        // Also remove coupons from code_activated_coupon_ids if their program applies_on current orders and the program does not give any points
        const toUnlink = order.code_activated_coupon_ids.filter(
            inverted((coupon) => {
                const program = coupon.program_id;
                if (
                    program.applies_on === "current" &&
                    pointsAddedPerProgram[program.id].length === 0
                ) {
                    return false;
                }
                return true;
            })
        );
        order.update({ code_activated_coupon_ids: [["unlink", ...toUnlink]] });
    },
    async activateCode(code) {
        const order = this.get_order();
        const rule = this.models["loyalty.rule"].find((rule) => {
            return rule.mode === "with_code" && (rule.promo_barcode === code || rule.code === code);
        });
        let claimableRewards = null;
        let coupon = null;
        if (rule) {
            const date_order = DateTime.fromSQL(order.date_order);
            if (
                rule.program_id.date_from &&
                date_order < rule.program_id.date_from.startOf("day")
            ) {
                return _t("That promo code program is not yet valid.");
            }
            if (rule.program_id.date_to && date_order > rule.program_id.date_to.endOf("day")) {
                return _t("That promo code program is expired.");
            }
            const program_pricelists = rule.program_id.pricelist_ids;
            if (
                program_pricelists.length > 0 &&
                (!order.pricelist_id || !program_pricelists.includes(order.pricelist_id.id))
            ) {
                return _t("That promo code program requires a specific pricelist.");
            }
            if (order.uiState.codeActivatedProgramRules.includes(rule.id)) {
                return _t("That promo code program has already been activated.");
            }
            order.uiState.codeActivatedProgramRules.push(rule.id);
            await this.orderUpdateLoyaltyPrograms();
            claimableRewards = order.getClaimableRewards(false, rule.program_id.id);
        } else {
            if (order.code_activated_coupon_ids.find((coupon) => coupon.code === code)) {
                return _t("That coupon code has already been scanned and activated.");
            }
            const customerId = order.get_partner() ? order.get_partner().id : false;
            const { successful, payload } = await this.data.call("pos.config", "use_coupon_code", [
                [this.config.id],
                code,
                order.date_order,
                customerId,
                order.pricelist_id ? order.pricelist_id.id : false,
            ]);
            if (successful) {
                // Allow rejecting a gift card that is not yet paid.
                const program = this.models["loyalty.program"].get(payload.program_id);
                if (program && program.program_type === "gift_card" && !payload.has_source_order) {
                    const confirmed = await ask(this.dialog, {
                        title: _t("Unpaid gift card"),
                        body: _t(
                            "This gift card is not linked to any order. Do you really want to apply its reward?"
                        ),
                    });
                    if (!confirmed) {
                        return _t("Unpaid gift card rejected.");
                    }
                }
                // TODO JCB: It's possible that the coupon is already loaded. We should check for that.
                //   - At the moment, creating a new one with existing id creates a duplicate.
                coupon = this.models["loyalty.card"].create({
                    id: payload.coupon_id,
                    code: code,
                    program_id: this.models["loyalty.program"].get(payload.program_id),
                    partner_id: this.models["res.partner"].get(payload.partner_id),
                    points: payload.points,
                    // TODO JCB: make the expiration_date work.
                    // expiration_date: payload.expiration_date,
                });
                order.update({ code_activated_coupon_ids: [["link", coupon]] });
                await this.orderUpdateLoyaltyPrograms();
                claimableRewards = order.getClaimableRewards(coupon.id);
            } else {
                return payload.error_message;
            }
        }
        if (claimableRewards && claimableRewards.length === 1) {
            if (
                claimableRewards[0].reward.reward_type !== "product" ||
                !claimableRewards[0].reward.multi_product
            ) {
                order._applyReward(claimableRewards[0].reward, claimableRewards[0].coupon_id);
                this.updateRewards();
            }
        }
        if (!rule && order.lines.length === 0 && coupon) {
            return _t(
                "Gift Card: %s\nBalance: %s",
                code,
                this.env.utils.formatCurrency(coupon.balance)
            );
        }
        return true;
    },
    async checkMissingCoupons() {
        // This function must stay sequential to avoid potential concurrency errors.
        const order = this.get_order();
        await mutex.exec(async () => {
            if (!order.invalidCoupons) {
                return;
            }
            order.invalidCoupons = false;
            const allCoupons = [];
            for (const pe of Object.values(order.uiState.couponPointChanges)) {
                if (pe.coupon_id > 0) {
                    allCoupons.push(pe.coupon_id);
                }
            }
            allCoupons.push(...order.code_activated_coupon_ids.map((coupon) => coupon.id));
            const couponsToFetch = allCoupons.filter(
                (elem) => !this.models["loyalty.card"].get(elem)
            );
            if (couponsToFetch.length) {
                await order.fetchCoupons([["id", "in", couponsToFetch]], couponsToFetch.length);
                // Remove coupons that could not be loaded from the db
                // TODO JCB: The following commented code doesn't seem to be necessary. Code activated coupons will always come from the backend.
                // this.uiState.codeActivatedCoupons = this.uiState.codeActivatedCoupons.filter(
                //     (coupon) => this.pos.couponCache[coupon.id]
                // );
                order.uiState.couponPointChanges = Object.fromEntries(
                    Object.entries(order.uiState.couponPointChanges).filter(([k, pe]) =>
                        this.models["loyalty.card"].get(pe.coupon_id)
                    )
                );
            }
        });
    },
    async addLineToCurrentOrder(vals, opt = {}, configure = true) {
        const product = vals.product_id;
        const order = this.get_order();
        const linkedPrograms =
            this.models["loyalty.program"].getBy("trigger_product_ids", product.id) || [];
        let selectedProgram = null;
        if (linkedPrograms.length > 1) {
            selectedProgram = await makeAwaitable(this.dialog, SelectionPopup, {
                title: _t("Select program"),
                list: linkedPrograms.map((program) => ({
                    id: program.id,
                    item: program,
                    label: program.name,
                })),
            });
            if (!selectedProgram) {
                return;
            }
        } else if (linkedPrograms.length === 1) {
            selectedProgram = linkedPrograms[0];
        }

        const orderTotal = this.get_order().get_total_with_tax();
        if (
            selectedProgram &&
            ["gift_card", "ewallet"].includes(selectedProgram.program_type) &&
            orderTotal < 0
        ) {
            opt.price_unit = -orderTotal;
        }
        if (selectedProgram && selectedProgram.program_type == "gift_card") {
            const shouldProceed = await this._setupGiftCardOptions(selectedProgram, opt);
            if (!shouldProceed) {
                return;
            }
        } else if (selectedProgram && selectedProgram.program_type == "ewallet") {
            const shouldProceed = await this.setupEWalletOptions(selectedProgram, opt);
            if (!shouldProceed) {
                return;
            }
        }
        const potentialRewards = this.getPotentialFreeProductRewards();
        const rewardsToApply = [];
        for (const reward of potentialRewards) {
            for (const reward_product_id of reward.reward.reward_product_ids) {
                if (reward_product_id.id == product.id) {
                    rewardsToApply.push(reward);
                }
            }
        }

        // move price_unit from opt to vals
        if (opt.price_unit) {
            vals.price_unit = opt.price_unit;
            delete opt.price_unit;
        }

        const result = await super.addLineToCurrentOrder(vals, opt, configure);

        await this.updatePrograms();
        if (rewardsToApply.length == 1) {
            const reward = rewardsToApply[0];
            order._applyReward(reward.reward, reward.coupon_id, { product });
        }
        this.updateRewards();

        return result;
    },
    /**
     * Sets up the options for the gift card product.
     * @param {object} program
     * @param {object} options
     * @returns {Promise<boolean>} whether to proceed with adding the product or not
     */
    async _setupGiftCardOptions(program, options) {
        options.quantity = 1;
        options.merge = false;
        options.eWalletGiftCardProgram = program;

        // If gift card program setting is 'scan_use', ask for the code.
        if (this.config.gift_card_settings == "scan_use") {
            const code = await makeAwaitable(this.dialog, TextInputPopup, {
                title: _t("Generate a Gift Card"),
                placeholder: _t("Enter the gift card code"),
            });
            if (!code) {
                return false;
            }
            const trimmedCode = code.trim();
            let nomenclatureRules = this.barcodeReader.parser.nomenclature.rules;
            if (this.barcodeReader.fallbackParser) {
                nomenclatureRules = nomenclatureRules.concat(
                    this.barcodeReader.fallbackParser.nomenclature.rules
                );
            }
            const couponRules = nomenclatureRules.filter((rule) => rule.type === "coupon");
            const isValidCoupon = couponRules.some((rule) => {
                const patterns = rule.pattern.split("|");
                return patterns.some((pattern) => trimmedCode.startsWith(pattern));
            });
            if (isValidCoupon) {
                // check if the code exist in the database
                // if so, use its balance, otherwise, use the unit price of the gift card product
                const fetchedGiftCard = await this.data.searchRead(
                    "loyalty.card",
                    [
                        ["code", "=", trimmedCode],
                        ["program_id", "=", program.id],
                    ],
                    ["points", "source_pos_order_id", "code", "program_id"]
                );

                // There should be maximum one gift card for a given code.
                const giftCard = fetchedGiftCard[0];
                if (giftCard && giftCard.source_pos_order_id) {
                    this.dialog.add(AlertDialog, {
                        title: _t("This gift card has already been sold"),
                        body: _t("You cannot sell a gift card that has already been sold."),
                    });
                    return false;
                }
                options.giftBarcode = trimmedCode;
                if (giftCard) {
                    // Use the balance of the gift card as the price of the orderline.
                    // NOTE: No need to convert the points to price because when opening a session,
                    // the gift card programs are made sure to have 1 point = 1 currency unit.
                    options.price_unit = giftCard.points;
                    options.giftCardId = giftCard.id;
                }
            } else {
                this.notification.add("Please enter a valid gift card code.");
                return false;
            }
        }
        return true;
    },
    async setupEWalletOptions(program, options) {
        options.quantity = 1;
        options.merge = false;
        options.eWalletGiftCardProgram = program;
        return true;
    },
    /**
     * Returns the reward such that when its reward product is added
     * in the order, it will be added as free. That is, when added,
     * it comes with the corresponding reward product line.
     */
    async pay() {
        const currentOrder = this.get_order();
        const eWalletLine = currentOrder
            .get_orderlines()
            .find((line) => line.getEWalletGiftCardProgramType() === "ewallet");

        if (eWalletLine && !currentOrder.get_partner()) {
            const confirmed = await ask(this.dialog, {
                title: _t("Customer needed"),
                body: _t("eWallet requires a customer to be selected"),
            });
            if (confirmed) {
                await this.selectPartner();
            }
        } else {
            return super.pay(...arguments);
        }
    },
    getPotentialFreeProductRewards() {
        const order = this.get_order();
        const allCouponPrograms = Object.values(order.uiState.couponPointChanges)
            .map((pe) => {
                return {
                    program_id: pe.program_id,
                    coupon_id: pe.coupon_id,
                };
            })
            .concat(
                order.code_activated_coupon_ids.map((coupon) => {
                    return {
                        program_id: coupon.program_id.id,
                        coupon_id: coupon.id,
                    };
                })
            );
        const result = [];
        for (const couponProgram of allCouponPrograms) {
            const program = this.models["loyalty.program"].get(couponProgram.program_id);
            if (
                program.pricelist_ids.length > 0 &&
                (!order.pricelist_id || !program.pricelist_ids.includes(order.pricelist_id.id))
            ) {
                continue;
            }

            const points = order._getRealCouponPoints(couponProgram.coupon_id);
            const hasLine = order.lines.filter((line) => !line.is_reward_line).length > 0;
            for (const reward of program.reward_ids.filter(
                (reward) => reward.reward_type == "product"
            )) {
                if (points < reward.required_points) {
                    continue;
                }
                // Loyalty program (applies_on == 'both') should needs an orderline before it can apply a reward.
                const considerTheReward =
                    program.applies_on !== "both" || (program.applies_on == "both" && hasLine);
                if (reward.reward_type === "product" && considerTheReward) {
                    let hasPotentialQty = true;
                    let potentialQty;
                    for (const { id } of reward.reward_product_ids) {
                        const product = this.models["product.product"].get(id);
                        potentialQty = order._computePotentialFreeProductQty(
                            reward,
                            product,
                            points
                        );
                        if (potentialQty <= 0) {
                            hasPotentialQty = false;
                        }
                    }
                    if (hasPotentialQty) {
                        result.push({
                            coupon_id: couponProgram.coupon_id,
                            reward: reward,
                            potentialQty,
                        });
                    }
                }
            }
        }
        return result;
    },

    //@override
    async processServerData(loadedData) {
        await super.processServerData(loadedData);

        this.partnerId2CouponIds = {};

        for (const reward of this.models["loyalty.reward"].getAll()) {
            this.compute_discount_product_ids(reward, this.models["product.product"].getAll());
        }

        for (const program of this.models["loyalty.program"].getAll()) {
            if (program.date_to) {
                program.date_to = DateTime.fromISO(program.date_to);
            }
            if (program.date_from) {
                program.date_from = DateTime.fromISO(program.date_from);
            }
        }
    },

    compute_discount_product_ids(reward, products) {
        const reward_product_domain = JSON.parse(reward.reward_product_domain);
        if (!reward_product_domain) {
            return;
        }

        const domain = new Domain(reward_product_domain);

        try {
            reward.update({
                all_discount_product_ids: [
                    ["link", ...products.filter((p) => domain.contains(p.serialize()))],
                ],
            });
        } catch (error) {
            if (!(error instanceof InvalidDomainError)) {
                throw error;
            }
            const index = this.models["loyalty.reward"].indexOf(reward);
            if (index != -1) {
                this.dialog.add(AlertDialog, {
                    title: _t("A reward could not be loaded"),
                    body: _t(
                        'The reward "%s" contain an error in its domain, your domain must be compatible with the PoS client',
                        this.models["loyalty.reward"].getAll()[index].description
                    ),
                });

                this.models["loyalty.reward"].delete(reward.id);
            }
        }
    },
    async initServerData() {
        await super.initServerData(...arguments);
        if (this.selectedOrderUuid) {
            this.updateRewards();
        }
    },
    /**
     * Fetches `loyalty.card` records from the server and adds/updates them in our cache.
     *
     * @param {domain} domain For the search
     * @param {int} limit Default to 1
     */
    async fetchCoupons(domain, limit = 1) {
        const result = await this.data.searchRead(
            "loyalty.card",
            domain,
            ["id", "points", "code", "partner_id", "program_id", "expiration_date"],
            { limit }
        );
        const couponList = [];
        for (const coupon of result) {
            this.partnerId2CouponIds[coupon.partner_id] =
                this.partnerId2CouponIds[coupon.partner_id] || new Set();
            this.partnerId2CouponIds[coupon.partner_id].add(coupon.id);
            couponList.push(coupon);
        }
        return couponList;
    },
    /**
     * Fetches a loyalty card for the given program and partner, put in cache afterwards
     *  if a matching card is found in the cache, that one is used instead.
     * If no card is found a local only card will be created until the order is validated.
     *
     * @param {int} programId
     * @param {int} partnerId
     */
    async fetchLoyaltyCard(programId, partnerId) {
        const coupon = this.models["loyalty.card"].find(
            (c) => c.partner_id?.id === partnerId && c.program_id?.id === programId
        );
        if (coupon) {
            return coupon;
        }
        const fetchedCoupons = await this.fetchCoupons([
            ["partner_id", "=", partnerId],
            ["program_id", "=", programId],
        ]);
        let dbCoupon = fetchedCoupons.length > 0 ? fetchedCoupons[0] : null;
        if (!dbCoupon) {
            dbCoupon = await this.models["loyalty.card"].create({
                id: loyaltyIdsGenerator(),
                code: null,
                program_id: this.models["loyalty.program"].get(programId),
                partner_id: this.models["res.partner"].get(partnerId),
                points: 0,
                expiration_date: null,
            });
        }
        return dbCoupon;
    },
    getLoyaltyCards(partner) {
        const loyaltyCards = [];
        if (this.partnerId2CouponIds[partner.id]) {
            this.partnerId2CouponIds[partner.id].forEach((couponId) =>
                loyaltyCards.push(this.models["loyalty.card"].get(couponId))
            );
        }
        return loyaltyCards;
    },
    /**
     * IMPROVEMENT: It would be better to update the local order object instead of creating a new one.
     *   - This way, we don't need to remember the lines linked to negative coupon ids and relink them after pushing the order.
     */
    preSyncAllOrders(orders) {
        super.preSyncAllOrders(orders);

        for (const order of orders) {
            Object.assign(
                this.couponByLineUuidCache,
                order.lines.reduce((agg, line) => {
                    if (line.coupon_id && line.coupon_id.id < 0) {
                        return { ...agg, [line.uuid]: line.coupon_id.id };
                    } else {
                        return agg;
                    }
                }, {})
            );
            Object.assign(
                this.rewardProductByLineUuidCache,
                order.lines.reduce((agg, line) => {
                    if (line.reward_product_id) {
                        return { ...agg, [line.uuid]: line.reward_product_id.id };
                    } else {
                        return agg;
                    }
                }, {})
            );
        }
    },
    postSyncAllOrders(orders) {
        super.postSyncAllOrders(orders);

        for (const order of orders) {
            for (const line of order.lines) {
                if (line.uuid in this.couponByLineUuidCache) {
                    line.update({
                        coupon_id: this.models["loyalty.card"].get(
                            this.couponByLineUuidCache[line.uuid]
                        ),
                    });
                }
            }
            for (const line of order.lines) {
                if (line.uuid in this.rewardProductByLineUuidCache) {
                    line.update({
                        reward_product_id: this.models["product.product"].get(
                            this.rewardProductByLineUuidCache[line.uuid]
                        ),
                    });
                }
            }
        }
    },
});
