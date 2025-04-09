import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Domain, InvalidDomainError } from "@web/core/domain";
import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { Mutex } from "@web/core/utils/concurrency";
import { serializeDate } from "@web/core/l10n/dates";

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
        this.couponByLineUuidCache = {};
        this.rewardProductByLineUuidCache = {};
        await super.setup(...arguments);
    },
    async updateOrder(order) {
        // Read value to trigger effect
        order?.lines?.length;
        await this.orderUpdateLoyaltyPrograms();
    },
    async selectPartner(partner) {
        const res = await super.selectPartner(partner);
        await this.updateRewards();
        return res;
    },
    async selectPricelist(pricelist) {
        await super.selectPricelist(pricelist);
        await this.updateRewards();
    },
    async resetPrograms() {
        const order = this.getOrder();
        order._resetPrograms();
        await this.orderUpdateLoyaltyPrograms();
        await this.updateRewards();
    },
    async orderUpdateLoyaltyPrograms() {
        if (!this.getOrder()) {
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

        const order = this.getOrder();
        if (!order || order.finalized) {
            return;
        }
        updateRewardsMutex.exec(() =>
            this.orderUpdateLoyaltyPrograms().then(async () => {
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
                        if (
                            (reward.reward_type == "product" &&
                                reward.program_id.applies_on !== "both") ||
                            (reward.program_id.applies_on == "both" && reward.reward_product_qty)
                        ) {
                            this.addLineToCurrentOrder({
                                product_id: reward.reward_product_id,
                                product_tmpl_id: reward.reward_product_id.product_tmpl_id,
                                qty: reward.reward_product_qty || 1,
                            });
                        }
                        order._applyReward(reward, coupon_id);
                        changed = true;
                    }
                }
                // Rewards may impact the number of points gained
                if (changed) {
                    await this.orderUpdateLoyaltyPrograms();
                }
                order._updateRewardLines();
            })
        );
    },
    async couponForProgram(program) {
        const order = this.getOrder();
        if (program.is_nominative) {
            return await this.fetchLoyaltyCard(program.id, order.getPartner().id);
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
        const order = this.getOrder();
        // 'order.delivery_provider_id' check is used for UrbanPiper orders (as loyalty points and rewards are not allowed for UrbanPiper orders)
        if (!order || order.delivery_provider_id) {
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
        for (const coupon of order._code_activated_coupon_ids) {
            programsToCheck.add(coupon.program_id.id);
        }
        const programs = [...programsToCheck].map((programId) =>
            this.models["loyalty.program"].get(programId)
        );
        const pointsAddedPerProgram = order.pointsForPrograms(programs);
        const generateKey = (pointObj) => {
            const { points, barcode = "", code = "", expiration_date = "" } = pointObj;
            return barcode
                ? `${points}_${barcode}`
                : code
                ? `${points}_null_${code}_${expiration_date}`
                : `${points}`;
        };
        for (const program of this.models["loyalty.program"].getAll()) {
            // Future programs may split their points per unit paid (gift cards for example), consider a non applicable program to give no points
            const pointsAdded = order._programIsApplicable(program)
                ? pointsAddedPerProgram[program.id]
                : [];
            // For programs that apply to both (loyalty) we always add a change of 0 points, if there is none, since it makes it easier to
            //  track for claimable rewards, and makes sure to load the partner's loyalty card.
            if (program.is_nominative && !pointsAdded.length && order.getPartner()) {
                pointsAdded.push({ points: 0 });
            }
            const oldChanges = changesPerProgram[program.id] || [];
            // Update point changes for those that exist
            for (let idx = 0; idx < Math.min(pointsAdded.length, oldChanges.length); idx++) {
                Object.assign(oldChanges[idx], pointsAdded[idx]);
            }
            if (pointsAdded.length < oldChanges.length || !order._programIsApplicable(program)) {
                const removedIds = oldChanges.map(
                    (pe) => !pointsAdded.includes(pe.points) && pe.coupon_id
                );
                const autoGiftCardPoints = pointsAdded
                    .filter((pa) => !pa.code)
                    .map((pa) => pa.points);
                const giftCodes = pointsAdded.filter((pa) => pa.code).map((pa) => pa.code);
                order.uiState.couponPointChanges = Object.fromEntries(
                    Object.entries(order.uiState.couponPointChanges).filter(([k, pe]) => {
                        if (pe.program_id !== program.id) {
                            return true;
                        } else if (pe.code && pe.manual && giftCodes.includes(pe.code)) {
                            return true;
                        } else if (!pe.code && autoGiftCardPoints.length) {
                            autoGiftCardPoints.pop();
                            return true;
                        } else if (!removedIds.includes(pe.coupon_id)) {
                            return true;
                        }
                    })
                );
            } else if (pointsAdded.length > oldChanges.length) {
                const pointsCount = pointsAdded.reduce((acc, pointObj) => {
                    const key = generateKey(pointObj);
                    acc[key] = (acc[key] || 0) + 1;
                    return acc;
                }, {});

                oldChanges.forEach((pointObj) => {
                    const key = generateKey(pointObj);
                    if (pointsCount[key] && pointsCount[key] > 0) {
                        pointsCount[key]--;
                    }
                });

                // Get new points added which are not in oldChanges
                const newPointsAdded = [];
                Object.keys(pointsCount).forEach((key) => {
                    const [points, barcode = "", code = "", expiration_date = ""] = key.split("_");
                    while (pointsCount[key] > 0) {
                        newPointsAdded.push({
                            points: Number(points),
                            barcode,
                            code,
                            expiration_date,
                        });
                        pointsCount[key]--;
                    }
                });

                for (const pa of newPointsAdded) {
                    const coupon = await this.couponForProgram(program);
                    const couponPointChange = {
                        points: pa.points,
                        program_id: program.id,
                        coupon_id: coupon.id,
                        barcode: pa.barcode,
                        appliedRules: pointsForProgramsCountedRules[program.id],
                    };
                    if (program && program.program_type === "gift_card") {
                        couponPointChange.product_id =
                            order.getSelectedOrderline()?.product_id?.id || null;
                        couponPointChange.expiration_date =
                            pa.expiration_date ||
                            serializeDate(luxon.DateTime.now().plus({ year: 1 }));
                        couponPointChange.code = pa.code;
                        couponPointChange.partner_id = pa.partner_id || false;
                        couponPointChange.manual = pa.code ? true : false;
                    }

                    order.uiState.couponPointChanges[coupon.id] = couponPointChange;
                }
            }
        }

        // Also remove coupons from _code_activated_coupon_ids if their program applies_on current orders and the program does not give any points
        const toUnlink = order._code_activated_coupon_ids.filter(
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
        order._code_activated_coupon_ids = [["unlink", ...toUnlink]];
    },
    async activateCode(code) {
        const order = this.getOrder();
        const rule = this.models["loyalty.rule"].find(
            (rule) =>
                rule.mode === "with_code" && (rule.promo_barcode === code || rule.code === code)
        );
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
                (!order.pricelist_id ||
                    !program_pricelists.some((pr) => pr.id === order.pricelist_id.id))
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
            if (order._code_activated_coupon_ids.find((coupon) => coupon.code === code)) {
                return _t("That coupon code has already been scanned and activated.");
            }
            const customerId = order.getPartner() ? order.getPartner().id : false;
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
                order._code_activated_coupon_ids = [["link", coupon]];
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
                this.env.utils.formatCurrency(coupon.points)
            );
        }
        return true;
    },
    async checkMissingCoupons() {
        // This function must stay sequential to avoid potential concurrency errors.
        const order = this.getOrder();
        await mutex.exec(async () => {
            if (!order.invalidCoupons) {
                return;
            }
            order.invalidCoupons = false;
            order.uiState.couponPointChanges = Object.fromEntries(
                Object.entries(order.uiState.couponPointChanges).filter(([k, pe]) =>
                    this.models["loyalty.card"].get(pe.coupon_id)
                )
            );
        });
    },
    async addLineToCurrentOrder(vals, opt = {}, configure = true) {
        if (!vals.product_tmpl_id && vals.product_id) {
            vals.product_tmpl_id = vals.product_id.product_tmpl_id;
        }

        const productTmpl = vals.product_tmpl_id;
        const productIds = productTmpl.product_variant_ids.map((v) => v.id);
        const order = this.getOrder();
        const linkedPrograms = [
            ...new Set(
                productIds
                    .flatMap(
                        (id) =>
                            this.models["loyalty.program"].getBy("trigger_product_ids", id) || []
                    )
                    .filter((p) => ["gift_card", "ewallet"].includes(p.program_type))
            ),
        ];
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

        const orderTotal = this.getOrder().getTotalWithTax();
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

        // move price_unit from opt to vals
        if (opt.price_unit !== undefined) {
            vals.price_unit = opt.price_unit;
            delete opt.price_unit;
        }

        const result = await super.addLineToCurrentOrder(vals, opt, configure);

        const rewardsToApply = [];
        for (const reward of potentialRewards) {
            for (const reward_product_id of reward.reward.reward_product_ids) {
                if (result.product_id.id == reward_product_id.id) {
                    rewardsToApply.push(reward);
                }
            }
        }

        await this.updatePrograms();
        if (rewardsToApply.length == 1) {
            const reward = rewardsToApply[0];
            order._applyReward(reward.reward, reward.coupon_id, {
                product: result.product_id,
            });
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
        const currentOrder = this.getOrder();
        const eWalletLine = currentOrder
            .getOrderlines()
            .find((line) => line.getEWalletGiftCardProgramType() === "ewallet");

        if (eWalletLine && !currentOrder.getPartner()) {
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
        const order = this.getOrder();
        const result = [];
        if (!order) {
            return result;
        }
        const allCouponPrograms = Object.values(order.uiState.couponPointChanges)
            .map((pe) => ({
                program_id: pe.program_id,
                coupon_id: pe.coupon_id,
            }))
            .concat(
                order._code_activated_coupon_ids.map((coupon) => ({
                    program_id: coupon.program_id.id,
                    coupon_id: coupon.id,
                }))
            );
        for (const couponProgram of allCouponPrograms) {
            const program = this.models["loyalty.program"].get(couponProgram.program_id);
            if (
                program.pricelist_ids.length > 0 &&
                (!order.pricelist_id ||
                    !program.pricelist_ids.some((pl) => pl.id === order.pricelist_id.id))
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
    async processServerData() {
        await super.processServerData();

        this.partnerId2CouponIds = {};

        this.computeDiscountProductIdsForAllRewards({
            ids: this.data.models["product.product"].getAllIds(),
        });

        this.models["product.product"].addEventListener(
            "create",
            this.computeDiscountProductIdsForAllRewards.bind(this)
        );

        for (const rule of this.models["loyalty.rule"].getAll()) {
            rule.validProductIds = new Set(rule.raw.valid_product_ids);
        }

        this.models["loyalty.card"].addEventListener("create", (records) => {
            records = records.ids.map((record) => this.models["loyalty.card"].get(record));
            this.computePartnerCouponIds(records);
        });
        this.computePartnerCouponIds();
    },

    computeDiscountProductIdsForAllRewards(data) {
        const products = this.models["product.product"].readMany(data.ids);
        for (const reward of this.models["loyalty.reward"].getAll()) {
            this.computeDiscountProductIds(reward, products);
        }
    },

    computePartnerCouponIds(loyaltyCards = null) {
        const cards = loyaltyCards || this.models["loyalty.card"].getAll();
        for (const card of cards) {
            if (!card.partner_id || card.id < 0) {
                continue;
            }

            if (!this.partnerId2CouponIds[card.partner_id.id]) {
                this.partnerId2CouponIds[card.partner_id.id] = new Set();
            }

            this.partnerId2CouponIds[card.partner_id.id].add(card.id);
        }
    },

    computeDiscountProductIds(reward, products) {
        const reward_product_domain = JSON.parse(reward.reward_product_domain);
        if (!reward_product_domain) {
            return;
        }

        const domain = new Domain(reward_product_domain);

        try {
            reward.all_discount_product_ids = [
                ["link", ...products.filter((p) => domain.contains(p.raw))],
            ];
        } catch (error) {
            if (!(error instanceof InvalidDomainError || error instanceof TypeError)) {
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

                reward.delete();
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
        return await this.data.searchRead(
            "loyalty.card",
            domain,
            this.data.fields["loyalty.card"],
            { limit }
        );
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
    async preSyncAllOrders(orders) {
        await super.preSyncAllOrders(orders);

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
                    if (line._reward_product_id) {
                        return { ...agg, [line.uuid]: line._reward_product_id.id };
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
                    line.coupon_id = this.models["loyalty.card"].get(
                        this.couponByLineUuidCache[line.uuid]
                    );
                }
            }
            for (const line of order.lines) {
                if (line.uuid in this.rewardProductByLineUuidCache) {
                    line._reward_product_id = this.models["product.product"].get(
                        this.rewardProductByLineUuidCache[line.uuid]
                    );
                }
            }
        }
    },
});
