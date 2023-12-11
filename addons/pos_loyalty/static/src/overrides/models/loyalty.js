/** @odoo-module **/

import { Order, Orderline } from "@point_of_sale/app/store/models";
import { Mutex } from "@web/core/utils/concurrency";
import { roundDecimals, roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";

const mutex = new Mutex(); // Used for sequential cache updates
const updateRewardsMutex = new Mutex();

function _newRandomRewardCode() {
    return (Math.random() + 1).toString(36).substring(3);
}

let nextId = -1;

let pointsForProgramsCountedRules = {};

export class PosLoyaltyCard {
    /**
     * @param {string} code coupon code
     * @param {number} id id of loyalty.card, negative if it is cache local only
     * @param {number} program_id id of loyalty.program
     * @param {number} partner_id id of res.partner
     * @param {number} balance points on the coupon, not counting the order's changes
     * @param {string} expiration_date
     */
    constructor(code, id, program_id, partner_id, balance, expiration_date = false) {
        this.code = code;
        this.id = id || nextId--;
        this.program_id = program_id;
        this.partner_id = partner_id;
        this.balance = balance;
        this.expiration_date = expiration_date && new Date(expiration_date);
    }

    isExpired() {
        return this.expiration_date && this.expiration_date < new Date();
    }
}

/**
 * Calculate the number of free items based on the given number
 * of items `number_items` and the rule: buy `n` take `m`.
 *
 * e.g.
 *```
 *      rule: buy 2 take 1                    rule: buy 2 take 3
 *     +------------+--------+--------+      +------------+--------+--------+
 *     |number_items| charged|    free|      |number_items| charged|    free|
 *     +------------+--------+--------+      +------------+--------+--------+
 *     |           1|       1|       0|      |           1|       1|       0|
 *     |           2|       2|       0|      |           2|       2|       0|
 *     |           3|       2|       1|      |           3|       2|       1|
 *     |           4|       3|       1|      |           4|       2|       2|
 *     |           5|       4|       1|      |           5|       2|       3|
 *     |           6|       4|       2|      |           6|       3|       3|
 *     |           7|       5|       2|      |           7|       4|       3|
 *     |           8|       6|       2|      |           8|       4|       4|
 *     |           9|       6|       3|      |           9|       4|       5|
 *     |          10|       7|       3|      |          10|       4|       6|
 *     +------------+--------+--------+      +------------+--------+--------+
 * ```
 *
 * @param {number} numberItems number of items
 * @param {number} n items to buy
 * @param {number} m item for free
 * @returns {number} number of free items
 */
function computeFreeQuantity(numberItems, n, m) {
    const factor = Math.trunc(numberItems / (n + m));
    const free = factor * m;
    const charged = numberItems - free;
    // adjust the calculated free quantities
    const x = (factor + 1) * n;
    const y = x + (factor + 1) * m;
    const adjustment = x <= charged && charged < y ? charged - x : 0;
    return Math.floor(free + adjustment);
}

patch(Orderline.prototype, {
    export_as_JSON() {
        const result = super.export_as_JSON(...arguments);
        result.is_reward_line = this.is_reward_line;
        result.reward_id = this.reward_id;
        result.reward_product_id = this.reward_product_id;
        result.coupon_id = this.coupon_id;
        result.reward_identifier_code = this.reward_identifier_code;
        result.points_cost = this.points_cost;
        result.giftBarcode = this.giftBarcode;
        result.giftCardId = this.giftCardId;
        result.eWalletGiftCardProgramId = this.eWalletGiftCardProgram
            ? this.eWalletGiftCardProgram.id
            : null;
        return result;
    },
    init_from_JSON(json) {
        if (json.is_reward_line) {
            this.is_reward_line = json.is_reward_line;
            this.reward_id = json.reward_id;
            this.reward_product_id = json.reward_product_id;
            // Since non existing coupon have a negative id, of which the counter is lost upon reloading
            //  we make sure that they are kept the same between after a reload between the order and the lines.
            this.coupon_id = this.order.oldCouponMapping[json.coupon_id] || json.coupon_id;
            this.reward_identifier_code = json.reward_identifier_code;
            this.points_cost = json.points_cost;
        }
        this.giftBarcode = json.giftBarcode;
        this.giftCardId = json.giftCardId;
        this.eWalletGiftCardProgram = this.pos.program_by_id[json.eWalletGiftCardProgramId];
        super.init_from_JSON(...arguments);
    },
    getEWalletGiftCardProgramType() {
        return this.eWalletGiftCardProgram && this.eWalletGiftCardProgram.program_type;
    },
    ignoreLoyaltyPoints({ program }) {
        return (
            ["gift_card", "ewallet"].includes(program.program_type) &&
            this.eWalletGiftCardProgram &&
            this.eWalletGiftCardProgram.id !== program.id
        );
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this._initializePrograms({});
        // Always start with invalid coupons so that coupon for this
        // order is properly assigned. @see _checkMissingCoupons
        this.invalidCoupons = true;
    },

    /** @override */
    getEmailItems() {
        return super
            .getEmailItems(...arguments)
            .concat(this.has_pdf_gift_card ? [_t("the gift cards")] : []);
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.disabledRewards = [...this.disabledRewards];
        json.codeActivatedProgramRules = this.codeActivatedProgramRules;
        json.codeActivatedCoupons = this.codeActivatedCoupons;
        json.couponPointChanges = this.couponPointChanges;
        return json;
    },
    init_from_JSON(json) {
        this.couponPointChanges = json.couponPointChanges;
        // Remapping of coupon_id for both couponPointChanges and Orderline.coupon_id
        this.oldCouponMapping = {};
        if (this.couponPointChanges) {
            for (const [key, pe] of Object.entries(this.couponPointChanges)) {
                if (!this.pos.program_by_id[pe.program_id]) {
                    // Remove points changes for programs that are not available anymore.
                    delete this.couponPointChanges[key];
                    continue;
                }
                if (pe.coupon_id > 0) {
                    continue;
                }
                const newId = nextId--;
                delete this.oldCouponMapping[pe.coupon_id];
                pe.coupon_id = newId;
                this.couponPointChanges[newId] = pe;
            }
        }
        super.init_from_JSON(...arguments);
        delete this.oldCouponMapping;
        this.disabledRewards = new Set(json.disabledRewards);
        this.codeActivatedProgramRules = json.codeActivatedProgramRules;
        this.codeActivatedCoupons = json.codeActivatedCoupons;
    },
    async pay() {
        const eWalletLine = this.get_orderlines().find(
            (line) => line.getEWalletGiftCardProgramType() === "ewallet"
        );
        if (eWalletLine && !this.get_partner()) {
            const { confirmed } = await this.env.services.popup.add(ConfirmPopup, {
                title: _t("Customer needed"),
                body: _t("eWallet requires a customer to be selected"),
            });
            if (confirmed) {
                const { confirmed, payload: newPartner } =
                    await this.env.services.pos.showTempScreen("PartnerListScreen", {
                        partner: null,
                    });
                if (confirmed) {
                    this.set_partner(newPartner);
                }
            }
        } else {
            return super.pay(...arguments);
        }
    },
    /**
     * We need to update the rewards upon changing the partner as it may impact the points available
     *  for rewards.
     *
     * @override
     */
    set_partner(partner) {
        const oldPartner = this.get_partner();
        super.set_partner(partner);
        if (this.couponPointChanges && oldPartner !== this.get_partner()) {
            // Remove couponPointChanges for cards in is_nominative programs.
            // This makes sure that counting of points on loyalty and ewallet programs is updated after partner changes.
            const loyaltyProgramIds = new Set(
                this.pos.programs
                    .filter((program) => program.is_nominative)
                    .map((program) => program.id)
            );
            for (const [key, pointChange] of Object.entries(this.couponPointChanges)) {
                if (loyaltyProgramIds.has(pointChange.program_id)) {
                    delete this.couponPointChanges[key];
                }
            }
            this._updateRewards();
        }
    },
    wait_for_push_order() {
        return (
            Object.keys(this.couponPointChanges || {}).length > 0 ||
            this._get_reward_lines().length ||
            super.wait_for_push_order(...arguments)
        );
    },
    /**
     * Add additional information for our ticket, such as new coupons and loyalty point gains.
     *
     * @override
     */
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.get_partner()) {
            result.loyaltyStats = this.getLoyaltyPoints();
            result.partner = this.get_partner();
        }
        result.new_coupon_info = this.new_coupon_info;
        return result;
    },
    //@override
    _get_ignored_product_ids_total_discount() {
        const productIds = super._get_ignored_product_ids_total_discount(...arguments);
        const giftCardPrograms = this.pos.programs.filter((p) => p.program_type === "gift_card");
        for (const program of giftCardPrograms) {
            const giftCardProductId = [...program.rules[0].valid_product_ids][0];
            if (giftCardProductId) {
                productIds.push(giftCardProductId);
            }
        }
        return productIds;
    },
    get_orderlines() {
        const orderlines = super.get_orderlines(this, arguments);
        const rewardLines = [];
        const nonRewardLines = [];
        for (const line of orderlines) {
            if (line.is_reward_line) {
                rewardLines.push(line);
            } else {
                nonRewardLines.push(line);
            }
        }
        return [...nonRewardLines, ...rewardLines];
    },
    _get_reward_lines() {
        if (this.orderlines) {
            return this.orderlines.filter((line) => line.is_reward_line);
        }
        return this.orderlines;
    },
    _get_regular_order_lines() {
        if (this.orderlines) {
            return this.orderlines.filter(
                (line) => !line.is_reward_line && !line.refunded_orderline_id
            );
        }
        return this.orderlines;
    },
    get_last_orderline() {
        const orderLines = this.orderlines.filter((line) => !line.is_reward_line);
        return orderLines[orderLines.length - 1];
    },
    set_pricelist(pricelist) {
        const oldPricelist = this.pricelist;
        super.set_pricelist(...arguments);
        if (this.couponPointChanges && oldPricelist !== pricelist) {
            // Remove couponPointChanges for cards in no longer available programs.
            // This makes sure that counting of points on loyalty and ewallet programs is updated after pricelist changes.
            const loyaltyProgramIds = new Set(
                this.pos.programs
                    .filter(
                        (program) =>
                            program.pricelist_ids.length > 0 &&
                            (!pricelist || !program.pricelist_ids.includes(pricelist.id))
                    )
                    .map((program) => program.id)
            );
            for (const [key, pointChange] of Object.entries(this.couponPointChanges)) {
                if (loyaltyProgramIds.has(pointChange.program_id)) {
                    delete this.couponPointChanges[key];
                }
            }
        }
        this._updateRewards();
    },
    set_orderline_options(line, options) {
        super.set_orderline_options(...arguments);
        if (options && options.is_reward_line) {
            line.is_reward_line = options.is_reward_line;
            line.reward_id = options.reward_id;
            line.reward_product_id = options.reward_product_id;
            line.coupon_id = options.coupon_id;
            line.reward_identifier_code = options.reward_identifier_code;
            line.points_cost = options.points_cost;
            line.price_type = "automatic";
        }
        line.giftBarcode = options.giftBarcode;
        line.giftCardId = options.giftCardId;
        line.eWalletGiftCardProgram = options.eWalletGiftCardProgram;
    },
    async _initializePrograms() {
        // When deleting a reward line, a popup will be displayed if the reward was automatic,
        //  if confirmed the reward is added to this list and will not be claimed automatically again.
        if (!this.disabledRewards) {
            this.disabledRewards = new Set();
        }
        // List of programs that require a code that are activated.
        if (!this.codeActivatedProgramRules) {
            this.codeActivatedProgramRules = [];
        }
        // List of coupons activated manually
        if (!this.codeActivatedCoupons) {
            this.codeActivatedCoupons = [];
        }
        // This field will hold the added points for each coupon.
        // Points lost are directly linked to the order lines.
        if (!this.couponPointChanges) {
            this.couponPointChanges = {};
        }
    },
    _resetPrograms() {
        this.disabledRewards = new Set();
        this.codeActivatedProgramRules = [];
        this.codeActivatedCoupons = [];
        this.couponPointChanges = {};
        this.orderlines.remove(this._get_reward_lines());
        this._updateRewards();
    },
    _updateRewards() {
        // Calls are not expected to take some time besides on the first load + when loyalty programs are made applicable
        if (this.pos.programs.length === 0) {
            return;
        }

        updateRewardsMutex.exec(() => {
            return this._updateLoyaltyPrograms().then(async () => {
                // Try auto claiming rewards
                const claimableRewards = this.getClaimableRewards(false, false, true);
                let changed = false;
                for (const { coupon_id, reward } of claimableRewards) {
                    if (
                        reward.program_id.rewards.length === 1 &&
                        !reward.program_id.is_nominative &&
                        (reward.reward_type !== "product" ||
                            (reward.reward_type == "product" && !reward.multi_product))
                    ) {
                        this._applyReward(reward, coupon_id);
                        changed = true;
                    }
                }
                // Rewards may impact the number of points gained
                if (changed) {
                    await this._updateLoyaltyPrograms();
                }
                this._updateRewardLines();
            });
        });
    },
    async _updateLoyaltyPrograms() {
        await this._checkMissingCoupons();
        await this._updatePrograms();
    },
    /**
     * Checks that all 'existing' coupons are in our cache, and if not load/update them.
     */
    async _checkMissingCoupons() {
        // This function must stay sequential to avoid potential concurrency errors.
        await mutex.exec(async () => {
            if (!this.invalidCoupons) {
                return;
            }
            this.invalidCoupons = false;
            const allCoupons = [];
            for (const pe of Object.values(this.couponPointChanges)) {
                if (pe.coupon_id > 0) {
                    allCoupons.push(pe.coupon_id);
                }
            }
            allCoupons.push(...this.codeActivatedCoupons.map((coupon) => coupon.id));
            const couponsToFetch = allCoupons.filter((elem) => !this.pos.couponCache[elem]);
            if (couponsToFetch.length) {
                await this.pos.fetchCoupons([["id", "in", couponsToFetch]], couponsToFetch.length);
                // Remove coupons that could not be loaded from the db
                this.codeActivatedCoupons = this.codeActivatedCoupons.filter(
                    (coupon) => this.pos.couponCache[coupon.id]
                );
                this.couponPointChanges = Object.fromEntries(
                    Object.entries(this.couponPointChanges).filter(
                        ([k, pe]) => this.pos.couponCache[pe.coupon_id]
                    )
                );
            }
        });
    },
    /**
     * Refreshes the currently applied rewards, if they are not applicable anymore they are removed.
     */
    _updateRewardLines() {
        if (!this.orderlines.length) {
            return;
        }
        const rewardLines = this._get_reward_lines();
        if (!rewardLines.length) {
            return;
        }
        const productRewards = [];
        const otherRewards = [];
        const paymentRewards = []; // Gift card and ewallet rewards are considered payments and must stay at the end
        for (const line of rewardLines) {
            const claimedReward = {
                reward: this.pos.reward_by_id[line.reward_id],
                coupon_id: line.coupon_id,
                args: {
                    product: line.reward_product_id,
                },
                reward_identifier_code: line.reward_identifier_code,
            };
            if (
                claimedReward.reward.program_id.program_type === "gift_card" ||
                claimedReward.reward.program_id.program_type === "ewallet"
            ) {
                paymentRewards.push(claimedReward);
            } else if (claimedReward.reward.reward_type === "product") {
                productRewards.push(claimedReward);
            } else if (!otherRewards.some(reward => reward.reward_identifier_code === claimedReward.reward_identifier_code)) {
                otherRewards.push(claimedReward);
            }
            this.orderlines.remove(line);
        }
        for (const claimedReward of productRewards.concat(otherRewards).concat(paymentRewards)) {
            // For existing coupons check that they are still claimed, they can exist in either `couponPointChanges` or `codeActivatedCoupons`
            if (
                !this.codeActivatedCoupons.find(
                    (coupon) => coupon.id === claimedReward.coupon_id
                ) &&
                !this.couponPointChanges[claimedReward.coupon_id]
            ) {
                continue;
            }
            this._applyReward(claimedReward.reward, claimedReward.coupon_id, claimedReward.args);
        }
    },
    /**
     * Update our couponPointChanges, meaning the points/coupons each program give etc.
     */
    async _updatePrograms() {
        const changesPerProgram = {};
        const programsToCheck = new Set();
        // By default include all programs that are considered 'applicable'
        for (const program of this.pos.programs) {
            if (this._programIsApplicable(program)) {
                programsToCheck.add(program.id);
            }
        }
        for (const pe of Object.values(this.couponPointChanges)) {
            if (!changesPerProgram[pe.program_id]) {
                changesPerProgram[pe.program_id] = [];
                programsToCheck.add(pe.program_id);
            }
            changesPerProgram[pe.program_id].push(pe);
        }
        for (const coupon of this.codeActivatedCoupons) {
            programsToCheck.add(coupon.program_id);
        }
        const programs = [...programsToCheck].map((programId) => this.pos.program_by_id[programId]);
        const pointsAddedPerProgram = this.pointsForPrograms(programs);
        for (const program of this.pos.programs) {
            // Future programs may split their points per unit paid (gift cards for example), consider a non applicable program to give no points
            const pointsAdded = this._programIsApplicable(program)
                ? pointsAddedPerProgram[program.id]
                : [];
            // For programs that apply to both (loyalty) we always add a change of 0 points, if there is none, since it makes it easier to
            //  track for claimable rewards, and makes sure to load the partner's loyalty card.
            if (program.is_nominative && !pointsAdded.length && this.get_partner()) {
                pointsAdded.push({ points: 0 });
            }
            const oldChanges = changesPerProgram[program.id] || [];
            // Update point changes for those that exist
            for (let idx = 0; idx < Math.min(pointsAdded.length, oldChanges.length); idx++) {
                Object.assign(oldChanges[idx], pointsAdded[idx]);
            }
            if (pointsAdded.length < oldChanges.length) {
                const removedIds = oldChanges.map((pe) => pe.coupon_id);
                this.couponPointChanges = Object.fromEntries(
                    Object.entries(this.couponPointChanges).filter(([k, pe]) => {
                        return !removedIds.includes(pe.coupon_id);
                    })
                );
            } else if (pointsAdded.length > oldChanges.length) {
                for (const pa of pointsAdded.splice(oldChanges.length)) {
                    const coupon = await this._couponForProgram(program);
                    this.couponPointChanges[coupon.id] = {
                        points: pa.points,
                        program_id: program.id,
                        coupon_id: coupon.id,
                        barcode: pa.barcode,
                        appliedRules: pointsForProgramsCountedRules[program.id],
                    };
                }
            }
        }
        // Also remove coupons from codeActivatedCoupons if their program applies_on current orders and the program does not give any points
        this.codeActivatedCoupons = this.codeActivatedCoupons.filter((coupon) => {
            const program = this.pos.program_by_id[coupon.program_id];
            if (
                program.applies_on === "current" &&
                pointsAddedPerProgram[program.id].length === 0
            ) {
                return false;
            }
            return true;
        });
    },
    /**
     * @typedef {{ won: number, spend: number, total: number, balance: number, name: string}} LoyaltyPoints
     * @typedef {{ couponId: number, program: object, points: LoyaltyPoints}} LoyaltyStat
     * @returns {Array<LoyaltyStat>}
     */
    getLoyaltyPoints() {
        // map: couponId -> LoyaltyPoints
        const loyaltyPoints = {};
        for (const pointChange of Object.values(this.couponPointChanges)) {
            const { coupon_id, points, program_id } = pointChange;
            const program = this.pos.program_by_id[program_id];
            if (program.program_type !== "loyalty") {
                // Not a loyalty program, skip
                continue;
            }
            const loyaltyCard = this.pos.couponCache[coupon_id] || /* or new card */ {
                id: coupon_id,
                balance: 0,
            };
            let [won, spent, total] = [0, 0, 0];
            const balance = loyaltyCard.balance;
            won += points - this._getPointsCorrection(program);
            if (coupon_id !== 0) {
                for (const line of this._get_reward_lines()) {
                    if (line.coupon_id === coupon_id) {
                        spent += line.points_cost;
                    }
                }
            }
            total = balance + won - spent;
            const name = program.portal_visible ? program.portal_point_name : _t("Points");
            loyaltyPoints[coupon_id] = {
                won: parseFloat(won.toFixed(2)),
                spent: parseFloat(spent.toFixed(2)),
                // Display total when order is ongoing.
                total: parseFloat(total.toFixed(2)),
                // Display balance when order is done.
                balance: parseFloat(balance.toFixed(2)),
                name,
                program,
            };
        }
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
        const rewardLines = this.orderlines.filter((line) => line.is_reward_line);
        let res = 0;
        for (const rule of program.rules) {
            for (const line of rewardLines) {
                const reward = this.pos.reward_by_id[line.reward_id];
                if (this._validForPointsCorrection(reward, line, rule)) {
                    if (rule.reward_point_mode === "order") {
                        res += rule.reward_point_amount;
                    } else if (rule.reward_point_mode === "money") {
                        res -= roundPrecision(
                            rule.reward_point_amount * line.get_price_with_tax(),
                            0.01
                        );
                    } else if (rule.reward_point_mode === "unit") {
                        res += rule.reward_point_amount * line.get_quantity();
                    }
                }
            }
        }
        return res;
    },
    /**
     * Checks if a reward line is valid for points correction.
     *
     * The function evaluates three conditions:
     * 1. The reward type must be 'product'.
     * 2. The reward line must be part of the rule.
     * 3. The reward line and the rule must be associated with the same program.
     */
    _validForPointsCorrection(reward, line, rule) {
        // Check if the reward type is free product
        if (reward.reward_type !== "product") {
            return false;
        }

        // Check if the reward line is part of the rule
        if (!(rule.any_product || rule.valid_product_ids.has(line.reward_product_id))) {
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
        const dbCoupon = this.pos.couponCache[coupon_id];
        if (dbCoupon) {
            points += dbCoupon.balance;
        }
        Object.values(this.couponPointChanges).some((pe) => {
            if (pe.coupon_id === coupon_id) {
                if (this.pos.program_by_id[pe.program_id].applies_on !== "future") {
                    points += pe.points;
                }
                // couponPointChanges is not supposed to have a coupon multiple times
                return true;
            }
            return false;
        });
        for (const line of this.get_orderlines()) {
            if (line.is_reward_line && line.coupon_id === coupon_id) {
                points -= line.points_cost;
            }
        }
        return points;
    },
    /**
     * Depending on the program type returns a new (local) instance of coupon or tries to retrieve the coupon in case of loyalty cards.
     * Existing coupons are put in a cache which is also used to fetch the coupons.
     *
     * @param {object} program
     */
    async _couponForProgram(program) {
        if (program.is_nominative) {
            return this.pos.fetchLoyaltyCard(program.id, this.get_partner().id);
        }
        // This type of coupons don't need to really exist up until validating the order, so no need to cache
        return new PosLoyaltyCard(null, null, program.id, (this.get_partner() || { id: -1 }).id, 0);
    },
    _programIsApplicable(program) {
        if (
            program.trigger === "auto" &&
            !program.rules.find(
                (rule) => rule.mode === "auto" || this.codeActivatedProgramRules.includes(rule.id)
            )
        ) {
            return false;
        }
        if (
            program.trigger === "with_code" &&
            !program.rules.find((rule) => this.codeActivatedProgramRules.includes(rule.id))
        ) {
            return false;
        }
        if (program.is_nominative && !this.get_partner()) {
            return false;
        }
        if (program.date_from && program.date_from > new Date()) {
            return false;
        }
        if (program.date_to && program.date_to < new Date()) {
            return false;
        }
        if (program.limit_usage && program.total_order_count >= program.max_usage) {
            return false;
        }
        if (
            program.pricelist_ids.length > 0 &&
            (!this.pricelist || !program.pricelist_ids.includes(this.pricelist.id))
        ) {
            return false;
        }
        return true;
    },
    /**
     * Computes how much points each program gives.
     *
     * @param {Array} programs list of loyalty.program
     * @returns {Object} Containing the points gained per program
     */
    pointsForPrograms(programs) {
        pointsForProgramsCountedRules = {};
        const totalTaxed = this.get_total_with_tax();
        const totalUntaxed = this.get_total_without_tax();
        const totalsPerProgram = Object.fromEntries(
            programs.map((program) => [program.id, { untaxed: totalUntaxed, taxed: totalTaxed }])
        );
        const orderLines = this.get_orderlines();
        for (const line of orderLines) {
            if (!line.reward_id) {
                continue;
            }
            const reward = this.pos.reward_by_id[line.reward_id];
            if (reward.reward_type !== "discount") {
                continue;
            }
            const rewardProgram = reward.program_id;
            for (const program of programs) {
                // Remove automatic discount and this program's discounts from the totals.
                if (program.id === rewardProgram.id || rewardProgram.trigger === "auto") {
                    totalsPerProgram[program.id]["taxed"] -= line.get_price_with_tax();
                    totalsPerProgram[program.id]["untaxed"] -= line.get_price_without_tax();
                }
            }
        }
        const result = {};
        for (const program of programs) {
            let points = 0;
            const splitPoints = [];
            for (const rule of program.rules) {
                if (
                    rule.mode === "with_code" &&
                    !this.codeActivatedProgramRules.includes(rule.id)
                ) {
                    continue;
                }
                const amountCheck =
                    (rule.minimum_amount_tax_mode === "incl" &&
                        totalsPerProgram[program.id]["taxed"]) ||
                    totalsPerProgram[program.id]["untaxed"];
                if (rule.minimum_amount > amountCheck) {
                    // NOTE: big doutes par rapport au fait de compter tous les produits
                    continue;
                }
                let totalProductQty = 0;
                // Only count points for paid lines.
                const qtyPerProduct = {};
                let orderedProductPaid = 0;
                for (const line of orderLines) {
                    if (
                        ((!line.reward_product_id &&
                            (rule.any_product ||
                                rule.valid_product_ids.has(line.get_product().id))) ||
                            (line.reward_product_id &&
                                (rule.any_product ||
                                    rule.valid_product_ids.has(line.reward_product_id)))) &&
                        !line.ignoreLoyaltyPoints({ program })
                    ) {
                        // We only count reward products from the same program to avoid unwanted feedback loops
                        if (line.reward_product_id) {
                            const reward = this.pos.reward_by_id[line.reward_id];
                            if (program.id !== reward.program_id) {
                                continue;
                            }
                        }
                        const lineQty = line.reward_product_id
                            ? -line.get_quantity()
                            : line.get_quantity();
                        totalProductQty += lineQty;
                        if (qtyPerProduct[line.reward_product_id || line.get_product().id]) {
                            qtyPerProduct[line.reward_product_id || line.get_product().id] +=
                                lineQty;
                        } else {
                            qtyPerProduct[line.reward_product_id || line.get_product().id] =
                                lineQty;
                        }
                        if (!line.is_reward_line) {
                            orderedProductPaid += line.get_price_with_tax();
                        }
                    }
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
                            ...Array.apply(null, Array(totalProductQty)).map((_) => {
                                return { points: rule.reward_point_amount };
                            })
                        );
                    } else if (rule.reward_point_mode === "money") {
                        for (const line of orderLines) {
                            if (
                                line.is_reward_line ||
                                !rule.valid_product_ids.has(line.get_product().id) ||
                                line.get_quantity() <= 0 ||
                                line.ignoreLoyaltyPoints({ program })
                            ) {
                                continue;
                            }
                            const pointsPerUnit = roundPrecision(
                                (rule.reward_point_amount * line.get_price_with_tax()) /
                                    line.get_quantity(),
                                0.01
                            );
                            if (pointsPerUnit > 0) {
                                splitPoints.push(
                                    ...Array.apply(null, Array(line.get_quantity())).map(() => {
                                        if (line.giftBarcode && line.get_quantity() == 1) {
                                            return {
                                                points: pointsPerUnit,
                                                barcode: line.giftBarcode,
                                                giftCardId: line.giftCardId,
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
                        points += roundPrecision(
                            rule.reward_point_amount * orderedProductPaid,
                            0.01
                        );
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
        return this.get_orderlines().filter(
            (line) => line.reward_id && this.pos.reward_by_id[line.reward_id].is_global_discount
        );
    },
    /**
     * Returns the number of product items in the order based on the given rule.
     * @param {*} rule
     */
    _computeNItems(rule) {
        return this._get_regular_order_lines().reduce((nItems, line) => {
            let increment = 0;
            if (rule.any_product || rule.valid_product_ids.has(line.product.id)) {
                increment = line.get_quantity();
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
        for (const rule of couponProgram.rules) {
            const amountToCompare =
                rule.minimum_amount_tax_mode == "incl" ? orderTotalWithTax : orderTotalWithoutTax;
            if (rule.minimum_amount > amountToCompare) {
                return false;
            }
            const nItems = this._computeNItems(rule);
            if (rule.minimum_qty > nItems) {
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
        const allCouponPrograms = Object.values(this.couponPointChanges)
            .map((pe) => {
                return {
                    program_id: pe.program_id,
                    coupon_id: pe.coupon_id,
                };
            })
            .concat(
                this.codeActivatedCoupons.map((coupon) => {
                    return {
                        program_id: coupon.program_id,
                        coupon_id: coupon.id,
                    };
                })
            );
        const result = [];
        const totalWithTax = this.get_total_with_tax();
        const totalWithoutTax = this.get_total_without_tax();
        const totalIsZero = totalWithTax === 0;
        const globalDiscountLines = this._getGlobalDiscountLines();
        const globalDiscountPercent = globalDiscountLines.length
            ? this.pos.reward_by_id[globalDiscountLines[0].reward_id].discount
            : 0;
        for (const couponProgram of allCouponPrograms) {
            const program = this.pos.program_by_id[couponProgram.program_id];
            if (
                program.pricelist_ids.length > 0 &&
                (!this.pricelist || !program.pricelist_ids.includes(this.pricelist.id))
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
            for (const reward of program.rewards) {
                if (points < reward.required_points) {
                    continue;
                }
                if (auto && this.disabledRewards.has(reward.id)) {
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
                if (reward.reward_type === "product" && !reward.multi_product) {
                    const product = this.pos.db.get_product_by_id(reward.reward_product_ids[0]);
                    unclaimedQty = this._computeUnclaimedFreeProductQty(
                        reward,
                        couponProgram.coupon_id,
                        product,
                        points
                    );
                    if (unclaimedQty <= 0) {
                        continue;
                    }
                }
                result.push({
                    coupon_id: couponProgram.coupon_id,
                    reward: reward,
                    potentialQty: unclaimedQty,
                });
            }
        }
        return result;
    },
    /**
     * Applies a reward to the order, `_updateRewards` is expected to be called right after.
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
                if (
                    rewardId != reward.id &&
                    this.pos.reward_by_id[rewardId].discount >= reward.discount
                ) {
                    return _t("A better global discount is already applied.");
                } else if (rewardId != rewardId.id) {
                    for (const line of globalDiscountLines) {
                        this.orderlines.remove(line);
                    }
                }
            }
        }
        args = args || {};
        const rewardLines = this._getRewardLineValues({
            reward: reward,
            coupon_id: coupon_id,
            product: args["product"] || null,
        });
        if (!Array.isArray(rewardLines)) {
            return rewardLines; // Returned an error.
        }
        if (!rewardLines.length) {
            return _t("The reward could not be applied.");
        }
        for (const rewardLine of rewardLines) {
            this.orderlines.add(this._createLineFromVals(rewardLine));
        }
        return true;
    },
    _createLineFromVals(vals) {
        vals["lst_price"] = vals["price"];
        const line = new Orderline(
            { env: this.env },
            { pos: this.pos, order: this, product: vals["product"] }
        );
        this.fix_tax_included_price(line);
        this.set_orderline_options(line, vals);
        return line;
    },
    /**
     * @param {loyalty.reward} reward
     * @returns the discountable and discountable per tax for this discount on order reward.
     */
    _getDiscountableOnOrder(reward) {
        let discountable = 0;
        const discountablePerTax = {};
        for (const line of this.get_orderlines()) {
            if (!line.get_quantity()) {
                continue;
            }
            const taxKey = line.get_taxes().map((t) => t.id);
            discountable += line.get_price_with_tax();
            if (!discountablePerTax[taxKey]) {
                discountablePerTax[taxKey] = 0;
            }
            discountablePerTax[taxKey] += line.get_base_price();
        }
        return { discountable, discountablePerTax };
    },
    /**
     * @returns the order's cheapest line
     */
    _getCheapestLine() {
        let cheapestLine;
        for (const line of this.get_orderlines()) {
            if (line.reward_id || !line.get_quantity()) {
                continue;
            }
            if (!cheapestLine || cheapestLine.price > line.price) {
                cheapestLine = line;
            }
        }
        return cheapestLine;
    },
    /**
     * @param {loyalty.reward} reward
     * @returns the discountable and discountable per tax for this discount on cheapest reward.
     */
    _getDiscountableOnCheapest(reward) {
        const cheapestLine = this._getCheapestLine();
        if (!cheapestLine) {
            return { discountable: 0, discountablePerTax: {} };
        }
        const taxKey = cheapestLine.get_taxes().map((t) => t.id);
        return {
            discountable: cheapestLine.price,
            discountablePerTax: Object.fromEntries([[taxKey, cheapestLine.price]]),
        };
    },
    /**
     * @param {loyalty.reward} reward
     * @returns all lines to which the reward applies.
     */
    _getSpecificDiscountableLines(reward) {
        const discountableLines = [];
        const applicableProducts = reward.all_discount_product_ids;
        for (const line of this.get_orderlines()) {
            if (!line.get_quantity()) {
                continue;
            }
            if (
                applicableProducts.has(line.get_product().id) ||
                applicableProducts.has(line.reward_product_id)
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
        const applicableProducts = reward.all_discount_product_ids;
        const linesToDiscount = [];
        const discountLinesPerReward = {};
        const orderLines = this.get_orderlines();
        const remainingAmountPerLine = {};
        for (const line of orderLines) {
            if (!line.get_quantity() || !line.price) {
                continue;
            }
            remainingAmountPerLine[line.cid] = line.get_price_with_tax();
            if (
                applicableProducts.has(line.get_product().id) ||
                (line.reward_product_id && applicableProducts.has(line.reward_product_id))
            ) {
                linesToDiscount.push(line);
            } else if (line.reward_id) {
                const lineReward = this.pos.reward_by_id[line.reward_id];
                if (lineReward.id === reward.id) {
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
            const lineReward = this.pos.reward_by_id[lines[0].reward_id];
            if (lineReward.reward_type !== "discount") {
                continue;
            }
            let discountedLines = orderLines;
            if (lineReward.discount_applicability === "cheapest") {
                cheapestLine = cheapestLine || this._getCheapestLine();
                discountedLines = [cheapestLine];
            } else if (lineReward.discount_applicability === "specific") {
                discountedLines = this._getSpecificDiscountableLines(lineReward);
            }
            if (!discountedLines.length) {
                continue;
            }
            const commonLines = linesToDiscount.filter((line) => discountedLines.includes(line));
            if (lineReward.discount_mode === "percent") {
                const discount = lineReward.discount / 100;
                for (const line of discountedLines) {
                    if (line.reward_id) {
                        continue;
                    }
                    if (lineReward.discount_applicability === "cheapest") {
                        remainingAmountPerLine[line.cid] *= 1 - discount / line.get_quantity();
                    } else {
                        remainingAmountPerLine[line.cid] *= 1 - discount;
                    }
                }
            } else {
                const nonCommonLines = discountedLines.filter(
                    (line) => !linesToDiscount.includes(line)
                );
                const discountedAmounts = lines.reduce((map, line) => {
                    map[line.get_taxes().map((t) => t.id)];
                    return map;
                }, {});
                const process = (line) => {
                    const key = line.get_taxes().map((t) => t.id);
                    if (!discountedAmounts[key] || line.reward_id) {
                        return;
                    }
                    const remaining = remainingAmountPerLine[line.cid];
                    const consumed = Math.min(remaining, discountedAmounts[key]);
                    discountedAmounts[key] -= consumed;
                    remainingAmountPerLine[line.cid] -= consumed;
                };
                nonCommonLines.forEach(process);
                commonLines.forEach(process);
            }
        }

        let discountable = 0;
        const discountablePerTax = {};
        for (const line of linesToDiscount) {
            discountable += remainingAmountPerLine[line.cid];
            const taxKey = line.get_taxes().map((t) => t.id);
            if (!discountablePerTax[taxKey]) {
                discountablePerTax[taxKey] = 0;
            }
            discountablePerTax[taxKey] +=
                line.get_base_price() *
                (remainingAmountPerLine[line.cid] / line.get_price_with_tax());
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
        discountable = Math.min(this.get_total_with_tax(), discountable);
        if (!discountable) {
            return [];
        }
        let maxDiscount = reward.discount_max_amount || Infinity;
        if (reward.discount_mode === "per_point") {
            maxDiscount = Math.min(
                maxDiscount,
                reward.discount * this._getRealCouponPoints(coupon_id)
            );
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
            return [
                {
                    product: discountProduct,
                    price: -Math.min(maxDiscount, discountable),
                    quantity: 1,
                    reward_id: reward.id,
                    is_reward_line: true,
                    coupon_id: coupon_id,
                    points_cost: pointCost,
                    reward_identifier_code: rewardCode,
                    merge: false,
                    tax_ids: [],
                },
            ];
        }
        const discountFactor = discountable ? Math.min(1, maxDiscount / discountable) : 1;
        const result = Object.entries(discountablePerTax).reduce((lst, entry) => {
            // Ignore 0 price lines
            if (!entry[1]) {
                return lst;
            }
            const taxIds = entry[0] === "" ? [] : entry[0].split(",").map((str) => parseInt(str));
            lst.push({
                product: discountProduct,
                price: -(entry[1] * discountFactor),
                quantity: 1,
                reward_id: reward.id,
                is_reward_line: true,
                coupon_id: coupon_id,
                points_cost: 0,
                reward_identifier_code: rewardCode,
                tax_ids: taxIds,
                merge: false,
            });
            return lst;
        }, []);
        if (result.length) {
            result[0]["points_cost"] = pointCost;
        }
        return result;
    },
    _isRewardProductPartOfRules(reward, product) {
        return (
            reward.program_id.rules.filter(
                (rule) => rule.any_product || rule.valid_product_ids.has(product.id)
            ).length > 0
        );
    },
    /**
     * Tries to compute how many free product can be given out for the given product.
     * Contrary to sale_loyalty, the product must be in the order lines in order to give it out
     *  (resulting in discount lines for the product's value).
     * As such we need to approximate the effect of removing 1 quantity on the counting of points in order
     *  to avoid feedback loops between giving a product and it removing the required points for it.
     *
     * @param {loyalty.reward} reward
     * @param {Integer} coupon_id
     * @param {Product} product
     * @returns {Integer} Available quantity to be given as reward for the given product
     */
    _computeUnclaimedFreeProductQty(reward, coupon_id, product, remainingPoints) {
        let claimed = 0;
        let available = 0;
        let shouldCorrectRemainingPoints = false;
        for (const line of this.get_orderlines()) {
            if (line.get_product().id === product.id) {
                available += line.get_quantity();
            } else if (line.reward_product_id === product.id) {
                if (line.reward_id == reward.id) {
                    claimed += line.get_quantity();
                } else {
                    shouldCorrectRemainingPoints = true;
                }
            }
        }
        let freeQty;
        if (reward.program_id.trigger == "auto") {
            if (this._isRewardProductPartOfRules(reward, product)) {
                // OPTIMIZATION: Pre-calculate the factors for each reward-product combination during the loading.
                // For points not based on quantity, need to normalize the points to compute free quantity.
                const appliedRulesIds = this.couponPointChanges[coupon_id].appliedRules;
                const appliedRules =
                    appliedRulesIds !== undefined
                        ? reward.program_id.rules.filter((rule) =>
                              appliedRulesIds.includes(rule.id)
                          )
                        : reward.program_id.rules;
                let factor = 0;
                let orderPoints = 0;
                for (const rule of appliedRules) {
                    if (rule.any_product || rule.valid_product_ids.has(product.id)) {
                        if (rule.reward_point_mode === "order") {
                            orderPoints += rule.reward_point_amount;
                        } else if (rule.reward_point_mode === "money") {
                            factor += roundPrecision(
                                rule.reward_point_amount * product.lst_price,
                                0.01
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
            if (this._isRewardProductPartOfRules(reward, product)) {
                const line = this.get_orderlines().find(
                    (line) => line.reward_product_id === product.id
                );
                // Compute the correction points once even if there are multiple reward lines.
                // This is because _getPointsCorrection is taking into account all the lines already.
                const claimedPoints = line ? this._getPointsCorrection(reward.program_id) : 0;
                return Math.floor(
                    ((remainingPoints - claimedPoints) / reward.required_points) *
                        reward.reward_product_qty
                );
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
    /**
     * @param {Object} args See `_applyReward`
     * @returns {Array} List of values to create the reward lines
     */
    _getRewardLineValuesProduct(args) {
        const reward = args["reward"];
        const product = this.pos.db.get_product_by_id(
            args["product"] || reward.reward_product_ids[0]
        );
        const points = this._getRealCouponPoints(args["coupon_id"]);
        const unclaimedQty = this._computeUnclaimedFreeProductQty(
            reward,
            args["coupon_id"],
            product,
            points
        );
        if (unclaimedQty <= 0) {
            return _t("There are not enough products in the basket to claim this reward.");
        }
        const claimable_count = reward.clear_wallet
            ? 1
            : Math.min(
                  Math.ceil(unclaimedQty / reward.reward_product_qty),
                  Math.floor(points / reward.required_points)
              );
        const cost = reward.clear_wallet ? points : claimable_count * reward.required_points;
        // In case the reward is the product multiple times, give it as many times as possible
        const freeQuantity = Math.min(unclaimedQty, reward.reward_product_qty * claimable_count);
        return [
            {
                product: reward.discount_line_product_id,
                price: -roundDecimals(
                    product.get_price(this.pricelist, freeQuantity),
                    this.pos.currency.decimal_places
                ),
                tax_ids: product.taxes_id,
                quantity: freeQuantity,
                reward_id: reward.id,
                is_reward_line: true,
                reward_product_id: product.id,
                coupon_id: args["coupon_id"],
                points_cost: cost,
                reward_identifier_code: _newRandomRewardCode(),
                merge: false,
            },
        ];
    },
    /**
     * Full routine for activating a code for the order.
     * If only one more reward is claimable after activating the code, that reward is claimed
     *  directly, to avoid more steps than necessary.
     * If more rewards are claimable, the employee will have to manually select the reward
     *  in the reward selection menu.
     *
     * @param {String} code
     * @returns true if everything went right, error message if not.
     */
    async _activateCode(code) {
        const rule = this.pos.rules.find((rule) => {
            return rule.mode === "with_code" && (rule.promo_barcode === code || rule.code === code);
        });
        let claimableRewards = null;
        let coupon = null;
        if (rule) {
            const program_pricelists = rule.program_id.pricelist_ids;
            if (
                program_pricelists.length > 0 &&
                (!this.pricelist || !program_pricelists.includes(this.pricelist.id))
            ) {
                return _t("That promo code program requires a specific pricelist.");
            }
            if (this.codeActivatedProgramRules.includes(rule.id)) {
                return _t("That promo code program has already been activated.");
            }
            this.codeActivatedProgramRules.push(rule.id);
            await this._updateLoyaltyPrograms();
            claimableRewards = this.getClaimableRewards(false, rule.program_id.id);
        } else {
            if (this.codeActivatedCoupons.find((coupon) => coupon.code === code)) {
                return _t("That coupon code has already been scanned and activated.");
            }
            const customerId = this.get_partner() ? this.get_partner().id : false;
            const { successful, payload } = await this.env.services.orm.call(
                "pos.config",
                "use_coupon_code",
                [
                    [this.pos.config.id],
                    code,
                    this.date_order,
                    customerId,
                    this.pricelist ? this.pricelist.id : false,
                ]
            );
            if (successful) {
                // Allow rejecting a gift card that is not yet paid.
                const program = this.pos.program_by_id[payload.program_id];
                if (program && program.program_type === "gift_card" && !payload.has_source_order) {
                    const { confirmed } = await this.env.services.popup.add(ConfirmPopup, {
                        title: _t("Unpaid gift card"),
                        body: _t(
                            "This gift card is not linked to any order. Do you really want to apply its reward?"
                        ),
                    });
                    if (!confirmed) {
                        return _t("Unpaid gift card rejected.");
                    }
                }
                coupon = new PosLoyaltyCard(
                    code,
                    payload.coupon_id,
                    payload.program_id,
                    payload.partner_id,
                    payload.points,
                    payload.expiration_date,
                );
                this.pos.couponCache[coupon.id] = coupon;
                this.codeActivatedCoupons.push(coupon);
                await this._updateLoyaltyPrograms();
                claimableRewards = this.getClaimableRewards(coupon.id);
            } else {
                return payload.error_message;
            }
        }
        if (claimableRewards && claimableRewards.length === 1) {
            if (
                claimableRewards[0].reward.reward_type !== "product" ||
                !claimableRewards[0].reward.multi_product
            ) {
                this._applyReward(claimableRewards[0].reward, claimableRewards[0].coupon_id);
                this._updateRewards();
            }
        }
        if (!rule && this.orderlines.length === 0 && coupon) {
            return _t(
                "Gift Card: %s\nBalance: %s",
                code,
                this.env.utils.formatCurrency(coupon.balance)
            );
        }
        return true;
    },
    async activateCode(code) {
        const res = await this._activateCode(code);
        if (res !== true) {
            this.env.services.pos_notification.add(res, 5000);
        }
    },
    isProgramsResettable() {
        const array = [
            this.disabledRewards,
            this.codeActivatedProgramRules,
            this.codeActivatedCoupons,
            this.couponPointChanges,
            this._get_reward_lines(),
        ];
        return array.some((elem) => elem.length > 0);
    },
    removeOrderline(lineToRemove) {
        if (lineToRemove.is_reward_line) {
            // Remove any line that is part of that same reward aswell.
            const linesToRemove = this.get_orderlines().filter((line) => {
                return (
                    line.reward_id === lineToRemove.reward_id &&
                    line.coupon_id === lineToRemove.coupon_id &&
                    line.reward_identifier_code === lineToRemove.reward_identifier_code
                );
            });
            for (const line of linesToRemove) {
                this._unlinkOrderline(line);
            }
            return true;
        } else {
            return super.removeOrderline(lineToRemove);
        }
    },
});
