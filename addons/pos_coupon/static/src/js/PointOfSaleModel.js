odoo.define('pos_coupon.PointOfSaleModel', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const session = require('web.session');
    const { patch } = require('web.utils');
    const { _t } = require('web.core');

    class Reward {
        static createKey(program_id, coupon_id) {
            return coupon_id ? `${program_id}-${coupon_id}` : `${program_id}`;
        }
        /**
         * Generated reward lines are based on the values stored in this object.
         *
         * @param {product.product} product product used in creating the reward line
         * @param {number} unit_price unit price of the reward
         * @param {number} quantity
         * @param {coupon.program} program
         * @param {number[]} tax_ids tax ids
         * @param {number?} coupon_id id of the coupon.coupon the generates this reward
         * @param {boolean=true} awarded identifies this object as 'awarded' or not.
         * @param {string?} reason reason why this reward is 'unawarded'.
         */
        constructor({
            product,
            unit_price,
            quantity,
            program,
            tax_ids,
            coupon_id = undefined,
            awarded = true,
            reason = undefined,
        }) {
            this.product = product;
            this.unit_price = unit_price;
            this.quantity = quantity;
            this.program = program;
            this.tax_ids = tax_ids;
            this.coupon_id = coupon_id;
            this._discountAmount = Math.abs(unit_price * quantity);
            this.status = {
                awarded,
                reason,
            };
            this._key = Reward.createKey(program.id, coupon_id);
        }
        /**
         * If the program's reward_type is 'product', return the product.product id of the
         * reward product.
         */
        get rewardedProductId() {
            return this.program.reward_type == 'product' && this.program.reward_product_id;
        }
        get discountAmount() {
            return this._discountAmount;
        }
        get key() {
            return this._key;
        }
    }

    class RewardsContainer {
        /**
         * The idea here is to have a data structure that will contain the awarded
         * and unawarded rewards based on the program and coupon combination.
         * If the program-coupon combination does not generate rewards because of
         * rules or because it is not the highest global discount, we create
         * an 'unawarded' `Reward` that corresponds to it, then we `add` it to
         * this data structure. Otherwise, we create an 'awarded' `Reward` object
         * then `add` it as well.
         *
         * We can then get the 'awarded' and 'unawarded' rewards via `getAwarded`
         * and `getUnawarded` methods, respectively.
         */
        constructor() {
            /**
             * @type {Record<string, Reward[]>} key is based on `program_id` and `coupon_id`.
             */
            this._rewards = {};
        }
        clear() {
            this._rewards = {};
        }
        /**
         * @param {Reward[]} rewards
         */
        add(rewards) {
            for (const reward of rewards) {
                if (reward.key in this._rewards) {
                    this._rewards[reward.key].push(reward);
                } else {
                    this._rewards[reward.key] = [reward];
                }
            }
        }
        getUnawarded() {
            return this._getFlattenRewards().filter((reward) => !reward.status.awarded);
        }
        getAwarded() {
            return this._getFlattenRewards().filter((reward) => reward.status.awarded);
        }
        _getFlattenRewards() {
            return Object.values(this._rewards).reduce((flatArr, arr) => [...flatArr, ...arr], []);
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
        let factor = Math.trunc(numberItems / (n + m));
        let free = factor * m;
        let charged = numberItems - free;
        // adjust the calculated free quantities
        let x = (factor + 1) * n;
        let y = x + (factor + 1) * m;
        let adjustment = x <= charged && charged < y ? charged - x : 0;
        return free + adjustment;
    }

    patch(PointOfSaleModel.prototype, 'pos_coupon', {
        _defineExtrasFields() {
            const result = this._super();
            const posOrder = result['pos.order'];
            posOrder.activePromoProgramIds = 'array';
            posOrder.bookedCouponCodes = 'object';
            return result;
        },
        _initDataDerived() {
            const result = this._super();
            result.validProductIds = {};
            result.validPartnerIds = {};
            result.discountSpecificProductIds = {};
            return result;
        },
        async _assignDataDerived() {
            await this._super();
            for (const program of this.getPrograms()) {
                this.data.derived.validProductIds[program.id] = new Set(program.valid_product_ids);
                this.data.derived.validPartnerIds[program.id] = new Set(program.valid_partner_ids);
                this.data.derived.discountSpecificProductIds[program.id] = new Set(
                    program.discount_specific_product_ids
                );
            }
            this.data.derived.rewardsContainerMap = {};
        },
        async afterLoadPosData() {
            await this._super(...arguments);
            const activeOrder = this.getActiveOrder();
            if (activeOrder) {
                await this._updateRewards(activeOrder);
            }
        },
        _defaultOrderExtras(uid) {
            const result = this._super(...arguments);
            result.activePromoProgramIds = this._getAutomaticPromoProgramIds();
            result.bookedCouponCodes = {};
            result.programIdsToGenerateCoupons = [];
            result.generatedCoupons = false;
            return result;
        },
        async _postPushOrder(order) {
            await this._super(...arguments);
            if (
                (order._extras.programIdsToGenerateCoupons && order._extras.programIdsToGenerateCoupons.length) ||
                this._getRewardOrderlines(order).length
            ) {
                const bookedCouponIds = new Set(
                    Object.values(order._extras.bookedCouponCodes)
                        .map((couponCode) => couponCode.coupon_id)
                        .filter((coupon_id) => coupon_id)
                );
                const usedCouponIds = this.getOrderlines(order)
                    .map((line) => line.coupon_id)
                    .filter((coupon_id) => coupon_id);
                for (const coupon_id of usedCouponIds) {
                    bookedCouponIds.delete(coupon_id);
                }
                const unusedCouponIds = [...bookedCouponIds.values()];
                order._extras.generatedCoupons = await this._rpc(
                    {
                        model: 'pos.order',
                        method: 'validate_coupon_programs',
                        args: [
                            [order._extras.server_id],
                            order._extras.programIdsToGenerateCoupons || [],
                            unusedCouponIds,
                        ],
                        kwargs: { context: session.user_context },
                    },
                    {}
                );
            }
        },
        getOrderlineJSON(orderline) {
            const result = this._super(...arguments);
            result.is_program_reward = orderline.is_program_reward;
            result.program_id = orderline.program_id;
            result.coupon_id = orderline.coupon_id;
            return result;
        },
        getOrderInfo(order) {
            const result = this._super(...arguments);
            result.generatedCoupons = order._extras.generatedCoupons;
            return result;
        },
        async addOrderline(order, orderline) {
            await this._super(...arguments);
            if (!orderline.is_program_reward) {
                await this._updateRewards(order);
            }
        },
        async actionUpdateOrderline(orderline) {
            const order = this.getRecord('pos.order', orderline.order_id);
            await this._super(...arguments);
            if (!orderline.is_program_reward) {
                await this._updateRewards(order);
            }
        },
        async actionDeleteOrderline(order, orderline) {
            const couponId = orderline.coupon_id;
            const programId = orderline.program_id;
            await this._super(...arguments);
            if (this.config.use_coupon_programs) {
                if (couponId) {
                    const codeStr = Object.values(order._extras.bookedCouponCodes).find(
                        (couponCode) => couponCode.coupon_id === couponId
                    ).code;
                    delete order._extras.bookedCouponCodes[codeStr];
                    await this._resetCoupons([couponId]);
                    this.ui.showNotification(_.str.sprintf(_t('Coupon (%s) has been deactivated.'), codeStr));
                } else if (programId) {
                    const index = order._extras.activePromoProgramIds.indexOf(programId);
                    order._extras.activePromoProgramIds.splice(index, 1);
                    this.ui.showNotification(
                        _.str.sprintf(
                            _t("'%s' program has been deactivated."),
                            this.getRecord('coupon.program', programId).name
                        )
                    );
                }
                const orderlinesToDelete = this._getRewardOrderlines(order).filter(
                    (line) => line.program_id === programId
                );
                for (const line of orderlinesToDelete) {
                    this._deleteOrderline(order, line);
                }
                await this._updateRewards(order);
            }
        },
        setRewardsContainer(orderId, rewardsContainer) {
            this.data.derived.rewardsContainerMap[orderId] = rewardsContainer;
        },
        getRewardsContainer(orderId) {
            return this.data.derived.rewardsContainerMap[orderId];
        },
        _getAutomaticPromoProgramIds() {
            return this.getPromoPrograms()
                .filter((program) => program.promo_code_usage === 'no_code_needed')
                .map((program) => program.id);
        },
        /**
         * These are the coupon programs that are activated
         * via coupon codes. RewardsContainer can only be generated if the coupon
         * program rules are satisfied.
         *
         * @returns {[coupon.program, number][]}
         */
        _getBookedCouponPrograms(order) {
            return Object.values(order._extras.bookedCouponCodes)
                .map((couponCode) => [
                    this.getRecord('coupon.program', couponCode.program_id),
                    parseInt(couponCode.coupon_id, 10),
                ])
                .filter(([program]) => {
                    return program.program_type === 'coupon_program';
                });
        },
        /**
         * These are the on_next_order promo programs that are activated
         * via coupon codes. RewardsContainer can be generated from this program
         * without checking the constraints.
         *
         * @returns {[coupon.program, number][]}
         */
        _getBookedPromoPrograms(order) {
            return Object.values(order._extras.bookedCouponCodes)
                .map((couponCode) => [
                    this.getRecord('coupon.program', couponCode.program_id),
                    parseInt(couponCode.coupon_id, 10),
                ])
                .filter(([program]) => {
                    return program.program_type === 'promotion_program';
                });
        },
        /**
         * These are the active on_current_order promo programs that will generate
         * rewards if the program constraints are fully-satisfied.
         *
         * @returns {[coupon.program, null][]}
         */
        _getActiveOnCurrentPromoPrograms(order) {
            return order._extras.activePromoProgramIds
                .map((program_id) => [this.getRecord('coupon.program', program_id), null])
                .filter(([program]) => {
                    return program.promo_applicability === 'on_current_order';
                });
        },
        /**
         * These are the active on_next_order promo programs that will generate
         * coupon codes if the program constraints are fully-satisfied.
         * @param {'pos.order'} order
         * @returns {[coupon.program, null][]}
         */
        _getActiveOnNextPromoPrograms: function (order) {
            return order._extras.activePromoProgramIds
                .map((program_id) => [this.getRecord('coupon.program', program_id), null])
                .filter(([program]) => {
                    return program.promo_applicability === 'on_next_order';
                });
        },
        async _checkProgramRules(order, program) {
            const { noTaxWithDiscount, withTaxWithDiscount } = this.getOrderTotals(order);
            // Check minimum amount
            const amountToCheck =
                program.rule_minimum_amount_tax_inclusion === 'tax_included' ? withTaxWithDiscount : noTaxWithDiscount;

            // TODO rule_minimum_amount has to be converted.
            if (!(amountToCheck >= program.rule_minimum_amount)) {
                return {
                    successful: false,
                    reason: 'Minimum amount for this program is not satisfied.',
                };
            }

            // Check minimum quantity
            const validQuantity = this._getRegularOrderlines(order)
                .filter((line) => {
                    return this.isValidProductOnProgram(program.id, line.product_id);
                })
                .reduce((total, line) => total + line.qty, 0);
            if (!(validQuantity >= program.rule_min_quantity)) {
                return {
                    successful: false,
                    reason: "Program's minimum quantity is not satisfied.",
                };
            }

            // Bypass other rules if program is coupon_program
            if (program.program_type === 'coupon_program') {
                return {
                    successful: true,
                };
            }

            // Check if valid customer
            if (program.rule_partners_domain && !this.isValidPartnerOnProgram(program.id, order.partner_id)) {
                return {
                    successful: false,
                    reason: "Current customer can't avail this program.",
                };
            }

            // Check rule date
            const ruleFrom = program.rule_date_from ? new Date(program.rule_date_from) : new Date(-8640000000000000);
            const ruleTo = program.rule_date_to ? new Date(program.rule_date_to) : new Date(8640000000000000);
            const orderDate = new Date();
            if (!(orderDate >= ruleFrom && orderDate <= ruleTo)) {
                return {
                    successful: false,
                    reason: 'Program already expired.',
                };
            }

            // Check max number usage
            if (program.maximum_use_number !== 0) {
                const [result] = await rpc
                    .query({
                        model: 'coupon.program',
                        method: 'read',
                        args: [program.id, ['total_order_count']],
                        kwargs: { context: session.user_context },
                    })
                    .catch(() => Promise.resolve([false])); // may happen because offline
                if (!result) {
                    return {
                        successful: false,
                        reason: 'Unable to get the number of usage of the program.',
                    };
                } else if (!(result.total_order_count < program.maximum_use_number)) {
                    return {
                        successful: false,
                        reason: "Program's maximum number of usage has been reached.",
                    };
                }
            }

            return {
                successful: true,
            };
        },
        /**
         * Sets the programs ids that will generate coupons based on the `rewardsContainer`.
         * If a program do not pass the rules-check, we add an 'unawarded' `Reward` in the
         * `rewardsContainer`.
         * @param {'pos.order'} order
         * @param {RewardsContainer} rewardsContainer
         */
        _setProgramIdsToGenerateCoupons: async function (order, rewardsContainer) {
            const programIdsToGenerateCoupons = [];
            for (const [program] of this._getActiveOnNextPromoPrograms(order)) {
                const { successful, reason } = await this._checkProgramRules(order, program);
                if (successful) {
                    programIdsToGenerateCoupons.push(program.id);
                } else {
                    const notAwarded = new Reward({ program, reason, awarded: false });
                    rewardsContainer.add([notAwarded]);
                }
            }
            order._extras.programIdsToGenerateCoupons = programIdsToGenerateCoupons;
        },
        /**
         * Create orderline rewards based on the `awarded` rewards from `rewardsContainer`.
         * @param {RewardsContainer} rewardsContainer
         * @returns {models.Orderline[]}
         */
        _getLinesToAdd(order, rewardsContainer) {
            return rewardsContainer
                .getAwarded()
                .map(({ product, unit_price, quantity, program, tax_ids, coupon_id }) => {
                    return this._createOrderline(
                        {
                            id: this._getNextId(),
                            qty: quantity,
                            price_unit: unit_price,
                            is_program_reward: true,
                            program_id: program.id,
                            tax_ids: tax_ids,
                            coupon_id: coupon_id,
                            product_id: product.id,
                            price_manually_set: true,
                        },
                        {}
                    );
                });
        },
        /**
         * Mutates `amountsToDiscount` to take into account the product rewards.
         *
         * @param {Record<string, number>} amountsToDiscount
         * @param {Set<number>} productIdsToAccount
         * @param {Reward[]} productRewards
         */
        _considerProductRewards: function (amountsToDiscount, productIdsToAccount, productRewards) {
            for (let reward of productRewards) {
                if (reward.rewardedProductId && productIdsToAccount.has(reward.rewardedProductId)) {
                    const key = reward.tax_ids.join(',');
                    amountsToDiscount[key] += reward.quantity * reward.unit_price;
                }
            }
        },
        _getGroupKey: function (line) {
            return this.getOrderlineTaxes(line)
                .map((tax) => tax.id)
                .join(',');
        },
        _createDiscountRewards: function (program, coupon_id, amountsToDiscount) {
            const discountRewards = Object.entries(amountsToDiscount).map(([tax_keys, amount]) => {
                let discountAmount = (amount * program.discount_percentage) / 100.0;
                discountAmount = Math.min(discountAmount, program.discount_max_amount || Infinity);
                return new Reward({
                    product: this.getRecord('product.product', program.discount_line_product_id),
                    unit_price: -discountAmount,
                    quantity: 1,
                    program: program,
                    tax_ids: tax_keys !== '' ? tax_keys.split(',').map((val) => parseInt(val, 10)) : [],
                    coupon_id: coupon_id,
                });
            });
            return [discountRewards, discountRewards.length > 0 ? null : 'No items to discount.'];
        },
        /**
         * This method is called via `collectRewards` inside `_calculateRewards`.
         * The purpose of this method is to create `Reward` objects based on the given
         * `program` and `coupon_id`.
         * It returns a tuple of rewards and reason if no rewards are created.
         *
         * @param {coupon.program} program
         * @param {number} coupon_id
         * @returns {[Reward[], string | null]}
         */
        _getProductRewards: function (order, program, coupon_id) {
            const totalQuantity = this._getRegularOrderlines(order)
                .filter((line) => {
                    return this.isValidProductOnProgram(program.id, line.product_id);
                })
                .reduce((quantity, line) => quantity + line.qty, 0);

            const freeQuantity = computeFreeQuantity(
                totalQuantity,
                program.rule_min_quantity,
                program.reward_product_quantity
            );
            if (freeQuantity === 0) {
                return [[], 'Zero free product quantity.'];
            } else {
                const rewardProduct = this.getRecord('product.product', program.reward_product_id);
                const discountLineProduct = this.getRecord('product.product', program.discount_line_product_id);
                return [
                    [
                        new Reward({
                            product: discountLineProduct,
                            unit_price: -rewardProduct.lst_price,
                            quantity: freeQuantity,
                            program: program,
                            tax_ids: rewardProduct.taxes_id,
                            coupon_id: coupon_id,
                        }),
                    ],
                    null,
                ];
            }
        },
        /**
         * This method is called via `collectRewards` inside `_calculateRewards`.
         * It returns fixed discount reward based on the given program.
         *
         * @param {coupon.program} program
         * @param {number} coupon_id
         * @returns {[Reward[], string | null]}
         */
        _getFixedDiscount: function (order, program, coupon_id) {
            const discountAmount = Math.min(program.discount_fixed_amount, program.discount_max_amount || Infinity);
            return [
                [
                    new Reward({
                        product: this.getRecord('product.product', program.discount_line_product_id),
                        unit_price: -discountAmount,
                        quantity: 1,
                        program: program,
                        tax_ids: [],
                        coupon_id: coupon_id,
                    }),
                ],
                null,
            ];
        },
        /**
         * This method is called via `collectRewards` inside `_calculateRewards`.
         * This returns discount rewards based on the program's specific products.
         * Amounts are grouped based on products tax ids (see `_getGroupKey`).
         * We also adjust the `amountsToDiscount` based on the rewarded products.
         *
         * @param {coupon.program} program
         * @param {number} coupon_id
         * @param {Reward[]} productRewards
         * @returns {[Reward[], string | null]}
         */
        _getSpecificDiscount: function (order, program, coupon_id, productRewards) {
            const productIdsToAccount = new Set();
            const amountsToDiscount = {};
            const nonZeroQtyOrderlines = this._getRegularOrderlines(order).filter(
                (line) => this.floatCompare(line.qty, 0) !== 0
            );
            for (const line of nonZeroQtyOrderlines) {
                if (this.isDiscountSpecificProductOnProgram(program.id, line.product_id)) {
                    const { priceWithoutTax } = this.getOrderlinePrices(line);
                    const key = this._getGroupKey(line);
                    if (!(key in amountsToDiscount)) {
                        amountsToDiscount[key] = priceWithoutTax;
                    } else {
                        amountsToDiscount[key] += priceWithoutTax;
                    }
                    productIdsToAccount.add(line.product_id);
                }
            }
            this._considerProductRewards(amountsToDiscount, productIdsToAccount, productRewards);
            return this._createDiscountRewards(program, coupon_id, amountsToDiscount);
        },
        /**
         * This method is called via `collectRewards` inside `_calculateRewards`.
         * It returns a discount reward for the cheapest item in the order. Cheapest
         * item is a single quantity with lowest price.
         *
         * @param {coupon.program} program
         * @param {number} coupon_id
         * @returns {[Reward[], string | null]}
         */
        _getOnCheapestProductDiscount: function (order, program, coupon_id) {
            const amountsToDiscount = {};
            const nonZeroQtyOrderlines = this._getRegularOrderlines(order).filter(
                (line) => this.floatCompare(line.qty, 0) !== 0
            );
            if (nonZeroQtyOrderlines.length > 0) {
                const [cheapestLine, cheapestUnitPrice] = nonZeroQtyOrderlines.reduce(
                    ([line, unitPrice], otherLine) => {
                        const otherLineUnitPrice = this.getOrderlineUnitPrice(otherLine);
                        if (unitPrice < otherLineUnitPrice) {
                            return [line, unitPrice];
                        } else {
                            return [otherLine, otherLineUnitPrice];
                        }
                    },
                    [nonZeroQtyOrderlines[0], this.getOrderlineUnitPrice(nonZeroQtyOrderlines[0])]
                );
                const key = this._getGroupKey(cheapestLine);
                amountsToDiscount[key] = cheapestUnitPrice;
            }
            return this._createDiscountRewards(program, coupon_id, amountsToDiscount);
        },
        /**
         * This method is called via `collectRewards` inside `_calculateRewards`.
         * This returns discount rewards based on all the orderlines. Amounts are grouped based
         * on products tax ids (see `_getGroupKey`). `amountsToDiscount` is adjusted
         * based on the rewarded products.
         *
         * @param {coupon.program} program
         * @param {number} coupon_id
         * @param {Reward[]} productRewards
         * @returns {[Reward[], string | null]}
         */
        _getOnOrderDiscountRewards: function (order, program, coupon_id, productRewards) {
            const productIdsToAccount = new Set();
            const amountsToDiscount = {};
            const nonZeroQtyOrderlines = this._getRegularOrderlines(order).filter(
                (line) => this.floatCompare(line.qty, 0) !== 0
            );
            for (const line of nonZeroQtyOrderlines) {
                const { priceWithoutTax } = this.getOrderlinePrices(line);
                const key = this._getGroupKey(line);
                if (!(key in amountsToDiscount)) {
                    amountsToDiscount[key] = priceWithoutTax;
                } else {
                    amountsToDiscount[key] += priceWithoutTax;
                }
                productIdsToAccount.add(line.product_id);
            }
            this._considerProductRewards(amountsToDiscount, productIdsToAccount, productRewards);
            return this._createDiscountRewards(program, coupon_id, amountsToDiscount);
        },
        /**
         * This method returns the segregated programs based on the types of rewards:
         * reward_type === 'product'
         *   1. freeProductPrograms
         * reward_type === 'discount'
         *   discount_type === 'fixed_amount'
         *     2. fixedAmountDiscountPrograms
         *   discount_type === 'percentage'
         *     discount_apply_on === 'specific_products'
         *       3. onSpecificPrograms
         *     discount_apply_on === 'cheapest_product'
         *       4. onCheapestPrograms
         *     discount_apply_on === 'on_order'
         *       5. onOrderPrograms
         *
         * It only includes the valid programs, those that passes the program rules.
         * This has side-effect of `add`ing unawarded rewards to the given rewardsContainer.
         */
        async _getValidActivePrograms(order, rewardsContainer) {
            const freeProductPrograms = [],
                fixedAmountDiscountPrograms = [],
                onSpecificPrograms = [],
                onCheapestPrograms = [],
                onOrderPrograms = [];

            function updateProgramLists(program, coupon_id) {
                if (program.reward_type === 'product') {
                    freeProductPrograms.push([program, coupon_id]);
                } else {
                    if (program.discount_type === 'fixed_amount') {
                        fixedAmountDiscountPrograms.push([program, coupon_id]);
                    } else if (program.discount_apply_on === 'specific_products') {
                        onSpecificPrograms.push([program, coupon_id]);
                    } else if (program.discount_apply_on === 'cheapest_product') {
                        onCheapestPrograms.push([program, coupon_id]);
                    } else {
                        onOrderPrograms.push([program, coupon_id]);
                    }
                }
            }

            for (const [program, coupon_id] of this._getBookedPromoPrograms(order)) {
                // Booked coupons from on next order promo programs do not need
                // checking of rules because checks are done before generating
                // coupons.
                updateProgramLists(program, coupon_id);
            }

            for (let [program, coupon_id] of [
                ...this._getBookedCouponPrograms(order),
                ...this._getActiveOnCurrentPromoPrograms(order),
            ]) {
                const { successful, reason } = await this._checkProgramRules(order, program);
                if (successful) {
                    updateProgramLists(program, coupon_id);
                } else {
                    const notAwarded = new Reward({ program, coupon_id, reason, awarded: false });
                    rewardsContainer.add([notAwarded]);
                }
            }

            return {
                freeProductPrograms,
                fixedAmountDiscountPrograms,
                onSpecificPrograms,
                onCheapestPrograms,
                onOrderPrograms,
            };
        },
        /**
         * In this method, we compute all the rewards as a result of `bookedCouponCodes`
         * and `activePromoProgramIds`. If a program do not generate a reward, we create
         * a `Reward` object with `awarded = false` then we `add` this object to the
         * `rewardsContainer`. Else, we create a `Reward` object with `awarded = true` then
         * we also `add` this to `rewardsContainer`. (See `collectRewards`.)
         *
         * The procedure in calculating the rewards is as follows:
         * - Compute the free product rewards. We will need its result in the calculation
         *   of discount rewards.
         * - Compute the fixed amount discount. This is independent of the free product
         *   rewards.
         * - Compute discount on specific products. Requires the free product rewards.
         * - Compute discount on cheapest product. Does not need the free product. We
         *   only discount the first item of the cheapest product.
         * - Compute discount on the whole order. This requires the free product rewards.
         * - We consider results of on order and cheapest product discounts as global
         *   discounts. We only choose one global discount, whichever gives the highest discount.
         * - We add the free product rewards, fixed amount discount, discount on specific
         *   products and the sole global discount to `rewardsContainer` then return it.
         *
         * @returns {RewardsContainer}
         */
        async _calculateRewards(order) {
            const rewardsContainer = new RewardsContainer();

            if (this._getRegularOrderlines(order).length === 0) {
                return rewardsContainer;
            }

            const {
                freeProductPrograms,
                fixedAmountDiscountPrograms,
                onSpecificPrograms,
                onCheapestPrograms,
                onOrderPrograms,
            } = await this._getValidActivePrograms(order, rewardsContainer);

            const collectRewards = (validPrograms, rewardGetter) => {
                const allRewards = [];
                for (let [program, coupon_id] of validPrograms) {
                    const [rewards, reason] = rewardGetter(order, program, coupon_id);
                    if (reason) {
                        const notAwarded = new Reward({ awarded: false, reason, program, coupon_id });
                        rewardsContainer.add([notAwarded]);
                    }
                    allRewards.push(...rewards);
                }
                return allRewards;
            };

            // - Gather the product rewards
            const freeProducts = collectRewards(freeProductPrograms, this._getProductRewards.bind(this));

            // - Gather the fixed amount discounts
            const fixedAmountDiscounts = collectRewards(fixedAmountDiscountPrograms, this._getFixedDiscount.bind(this));

            // - Gather the specific discounts
            const specificDiscountGetter = (order, program, coupon_id) => {
                return this._getSpecificDiscount(order, program, coupon_id, freeProducts);
            };
            const specificDiscounts = collectRewards(onSpecificPrograms, specificDiscountGetter);

            // - Collect the discounts from on order and on cheapest discount programs.
            const globalDiscounts = [];
            const onOrderDiscountGetter = (order, program, coupon_id) => {
                return this._getOnOrderDiscountRewards(order, program, coupon_id, freeProducts);
            };
            globalDiscounts.push(...collectRewards(onOrderPrograms, onOrderDiscountGetter));
            globalDiscounts.push(...collectRewards(onCheapestPrograms, this._getOnCheapestProductDiscount.bind(this)));

            // - Group the discounts by program id.
            const groupedGlobalDiscounts = {};
            for (let discount of globalDiscounts) {
                const key = [discount.program.id, discount.coupon_id].join(',');
                if (!(key in groupedGlobalDiscounts)) {
                    groupedGlobalDiscounts[key] = [discount];
                } else {
                    groupedGlobalDiscounts[key].push(discount);
                }
            }

            // - We select the group of discounts with highest total amount.
            // Note that the result is an Array that might contain more than one
            // discount lines. This is because discounts are grouped by tax.
            let currentMaxTotal = 0;
            let currentMaxKey = null;
            for (let key in groupedGlobalDiscounts) {
                const discountRewards = groupedGlobalDiscounts[key];
                const newTotal = discountRewards.reduce((sum, discReward) => sum + discReward.discountAmount, 0);
                if (newTotal > currentMaxTotal) {
                    currentMaxTotal = newTotal;
                    currentMaxKey = key;
                }
            }
            const theOnlyGlobalDiscount = currentMaxKey
                ? groupedGlobalDiscounts[currentMaxKey].filter((discountReward) => discountReward.discountAmount !== 0)
                : [];

            // - Get the messages for the discarded global_discounts
            if (theOnlyGlobalDiscount.length > 0) {
                const theOnlyGlobalDiscountKey = [
                    theOnlyGlobalDiscount[0].program.id,
                    theOnlyGlobalDiscount[0].coupon_id,
                ].join(',');
                for (let [key, discounts] of Object.entries(groupedGlobalDiscounts)) {
                    if (key !== theOnlyGlobalDiscountKey) {
                        const notAwarded = new Reward({
                            program: discounts[0].program,
                            coupon_id: discounts[0].coupon_id,
                            reason: 'Not the greatest global discount.',
                            awarded: false,
                        });
                        rewardsContainer.add([notAwarded]);
                    }
                }
            }

            // - Add the calculated rewards.
            rewardsContainer.add([
                ...freeProducts,
                ...fixedAmountDiscounts,
                ...specificDiscounts,
                ...theOnlyGlobalDiscount,
            ]);

            return rewardsContainer;
        },
        /**
         * @returns {[models.Orderline[], RewardsContainer]}
         */
        async _getNewRewardLines(order) {
            const rewardsContainer = await this._calculateRewards(order);
            // We set the programs that will generate coupons after validation of this order.
            // @see `_postPushOrder`.
            await this._setProgramIdsToGenerateCoupons(order, rewardsContainer);
            // Create reward orderlines here based on the content of `rewardsContainer` field.
            return [this._getLinesToAdd(order, rewardsContainer), rewardsContainer];
        },
        isValidProductOnProgram(programId, productId) {
            const productIds = this.data.derived.validProductIds[programId];
            return productIds ? productIds.has(productId) : false;
        },
        isValidPartnerOnProgram(programId, productId) {
            const partnerIds = this.data.derived.validPartnerIds[programId];
            return partnerIds ? partnerIds.has(productId) : false;
        },
        isDiscountSpecificProductOnProgram(programId, productId) {
            const productIds = this.data.derived.discountSpecificProductIds[programId];
            return productIds ? productIds.has(productId) : false;
        },
        getPrograms() {
            return this.getRecords('coupon.program');
        },
        getPromoPrograms() {
            return this.getPrograms().filter((program) => program.program_type === 'promotion_program');
        },
        getCouponPrograms() {
            return this.getPrograms().filter((program) => program.program_type === 'coupon_program');
        },
        _getRegularOrderlines(order) {
            return this.getOrderlines(order).filter((line) => !line.is_program_reward);
        },
        _getRewardOrderlines(order) {
            return this.getOrderlines(order).filter((line) => line.is_program_reward);
        },
        async _resetCoupons(couponIds) {
            await this._rpc(
                {
                    model: 'coupon.coupon',
                    method: 'write',
                    args: [couponIds, { state: 'new' }],
                    kwargs: { context: session.user_context },
                },
                {}
            );
        },
        async _updateRewards(order) {
            if (!this.config.use_coupon_programs) return;
            const rewardLines = this._getRewardOrderlines(order);
            for (const rewardLine of rewardLines) {
                this._deleteOrderline(order, rewardLine);
            }
            const [newRewardLines, rewardsContainer] = await this._getNewRewardLines(order);
            this.setRewardsContainer(order.id, rewardsContainer);
            for (const rewardLine of newRewardLines) {
                await this.addOrderline(order, rewardLine, false);
            }
            if (!this.getActiveOrderline(order)) {
                const lines = this._getRegularOrderlines(order);
                if (lines.length) {
                    this.actionSelectOrderline(order, lines[lines.length - 1].id);
                }
            }
        },
        async actionActivateCode(order, code) {
            const promoProgram = this.getPromoPrograms().find(
                (program) => program.promo_barcode === code || program.promo_code === code
            );
            const activePromoProgramIds = order._extras.activePromoProgramIds;
            const bookedCouponCodes = order._extras.bookedCouponCodes;
            if (promoProgram && activePromoProgramIds.includes(promoProgram.id)) {
                this.ui.showNotification(_t('That promo code program has already been activated.'));
            } else if (promoProgram) {
                activePromoProgramIds.push(promoProgram.id);
                await this._updateRewards(order);
            } else if (code in bookedCouponCodes) {
                this.ui.showNotification(_t('That coupon code has already been scanned and activated.'));
            } else {
                const programIdsWithScannedCoupon = Object.values(bookedCouponCodes).map(
                    (couponCode) => couponCode.program_id
                );
                const { successful, payload } = await this._rpc({
                    model: 'pos.config',
                    method: 'use_coupon_code',
                    args: [
                        [this.config.id],
                        code,
                        order.date_order,
                        order.partner_id || false,
                        programIdsWithScannedCoupon,
                    ],
                    kwargs: { context: session.user_context },
                });
                if (successful) {
                    bookedCouponCodes[code] = { code, coupon_id: payload.coupon_id, program_id: payload.program_id };
                    await this._updateRewards(order);
                } else {
                    this.ui.showNotification(payload.error_message);
                }
            }
        },
        async actionResetPrograms(order) {
            let deactivatedCount = 0;
            if (order._extras.bookedCouponCodes) {
                const couponIds = Object.values(order._extras.bookedCouponCodes).map(
                    (couponCode) => couponCode.coupon_id
                );
                if (couponIds.length > 0) {
                    await this._resetCoupons(couponIds);
                }
                order._extras.bookedCouponCodes = {};
                deactivatedCount += couponIds.length;
            }
            if (order._extras.activePromoProgramIds) {
                const codeNeededPromoProgramIds = order._extras.activePromoProgramIds.filter((program_id) => {
                    return this.getRecord('coupon.program', program_id).promo_code_usage === 'code_needed';
                });
                order._extras.activePromoProgramIds = this._getAutomaticPromoProgramIds();
                deactivatedCount += codeNeededPromoProgramIds.length;
            }
            await this._updateRewards(order);
            if (deactivatedCount > 0) {
                this.ui.showNotification(_t('Active coupons and promo codes were deactivated.'));
            }
        },
    });

    return PointOfSaleModel;
});
