odoo.define('pos_coupon.pos', function (require) {
    'use strict';

    /**
     * When pos_coupon is active (`use_coupon_programs == true`), reward lines
     * are generated for each order. Everytime an order is updated ('update-rewards'
     * event is triggered), the reward lines are recalculated. Generated reward lines
     * are computed based on `bookedCouponCodes` and `activePromoProgramIds` which are
     * initialized in `_initializePrograms`. `activePromoProgramIds` start with the
     * automatic promo programs - promo programs with `promo_code_usage == 'no_code_needed'`.
     * `bookedCouponCodes` and `activePromoProgramIds` containers are then updated when
     * scanning codes (see `activateCode`).
     *
     * In short, `bookedCouponCodes` and `activePromoProgramIds` are populated via
     * `activateCode`, then whenever 'update-rewards' is triggered, its callback updates
     * the reward lines based on the values stored in `bookedCouponCodes` and
     * `activePromoProgramIds`
     */

    const models = require('point_of_sale.models');
    const rpc = require('web.rpc');
    const session = require('web.session');
    const concurrency = require('web.concurrency');
    const { Gui } = require('point_of_sale.Gui');
    const { float_is_zero,round_decimals } = require('web.utils');

    const dp = new concurrency.DropPrevious();

    class CouponCode {
        /**
         * @param {string} code coupon code
         * @param {number} coupon_id id of coupon.coupon
         * @param {numnber} program_id id of coupon.program
         */
        constructor(code, coupon_id, program_id) {
            this.code = code;
            this.coupon_id = coupon_id;
            this.program_id = program_id;
        }
    }

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
            return (
                this.program.reward_type == 'product' &&
                this.program.reward_product_id &&
                this.program.reward_product_id[0]
            );
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

    // Some utility functions

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

    // Load the products used for creating program reward lines.
    var existing_models = models.PosModel.prototype.models;
    var product_index = _.findIndex(existing_models, function (model) {
        return model.model === 'product.product';
    });
    var product_model = existing_models[product_index];
    models.load_models([
        {
            model: 'coupon.program',
            fields: [],
            domain: function (self) {
                return [['id', 'in', self.config.program_ids]];
            },
            loaded: function (self, programs) {
                self.programs = programs;
                self.coupon_programs_by_id = {};
                self.coupon_programs = [];
                self.promo_programs = [];
                for (let program of self.programs) {
                    // index by id
                    self.coupon_programs_by_id[program.id] = program;
                    // separate coupon programs from promo programs
                    if (program.program_type === 'coupon_program') {
                        self.coupon_programs.push(program);
                    } else {
                        self.promo_programs.push(program);
                    }
                    // cast some arrays to Set for faster membership checking
                    program.valid_product_ids = new Set(program.valid_product_ids);
                    program.valid_partner_ids = new Set(program.valid_partner_ids);
                    program.discount_specific_product_ids = new Set(program.discount_specific_product_ids);
                }
            },
        },
        {
            model: product_model.model,
            fields: product_model.fields,
            order: product_model.order,
            domain: function (self) {
                const discountLineProductIds = self.programs.map((program) => program.discount_line_product_id[0]);
                const rewardProductIds = self.programs.map((program) => program.reward_product_id[0]);
                return [['id', 'in', discountLineProductIds.concat(rewardProductIds)]];
            },
            context: product_model.context,
            loaded: product_model.loaded,
        },
    ]);

    var _posmodel_super = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function () {
            _posmodel_super.initialize.apply(this, arguments);
            this.ready.then(() => {
                if (this.get('selectedOrder')) {
                    this.get('selectedOrder').trigger('update-rewards');
                }
            });
        },
    });

    /**
     * @listens 'update-rewards'
     * @listens 'reset-coupons' calls resetCoupons when triggered.
     * @emits 'rewards-updated' emitted after 'update-rewards' callback.
     */
    var _order_super = models.Order.prototype;
    models.Order = models.Order.extend({
        // OVERIDDEN METHODS

        initialize: function () {
            _order_super.initialize.apply(this, arguments);
            this.on(
                'update-rewards',
                () => {
                    if (!this.pos.config.use_coupon_programs) return;
                    dp.add(this._getNewRewardLines()).then(([newRewardLines, rewardsContainer]) => {
                        newRewardLines.forEach(line => this.add_orderline(line));
                        // We need this for the rendering of ActivePrograms component.
                        this.rewardsContainer = rewardsContainer;
                        // Send a signal that the rewardsContainer are updated.
                        this.trigger('rewards-updated');
                    }).catch(() => { /* catch the reject of dp when calling `add` to avoid unhandledrejection */ });
                },
                this
            );
            this.on('reset-coupons', this.resetCoupons, this);
            this._initializePrograms();
            return this;
        },
        init_from_JSON: function (json) {
            this.bookedCouponCodes = json.bookedCouponCodes ? json.bookedCouponCodes : {};
            this.activePromoProgramIds = json.activePromoProgramIds ? json.activePromoProgramIds : [];
            _order_super.init_from_JSON.apply(this, arguments);
        },
        export_as_JSON: function () {
            let json = _order_super.export_as_JSON.apply(this, arguments);
            return Object.assign(json, {
                bookedCouponCodes: this.bookedCouponCodes,
                activePromoProgramIds: this.activePromoProgramIds,
            });
        },
        set_orderline_options: function (orderline, options) {
            _order_super.set_orderline_options.apply(this, [orderline, options]);
            if (options && options.is_program_reward) {
                orderline.is_program_reward = true;
                orderline.program_id = options.program_id;
                orderline.coupon_id = options.coupon_id;
            }
        },
        /**
         * This function's behavior is modified so that the reward lines are
         * rendered at the bottom of the orderlines list.
         */
        get_orderlines: function () {
            const orderlines = _order_super.get_orderlines.apply(this, arguments);
            const rewardLines = [];
            const nonRewardLines = [];
            for (const line of orderlines) {
                if (line.is_program_reward) {
                    rewardLines.push(line);
                } else {
                    nonRewardLines.push(line);
                }
            }
            return [...nonRewardLines, ...rewardLines];
        },
        _getRegularOrderlines: function () {
            const orderlines = _order_super.get_orderlines.apply(this, arguments);
            const is_gift_card_product = (line) => this.pos.config.gift_card_product_id && line.product.id === this.pos.config.gift_card_product_id[0];
            const is_tips_product = (line) => this.pos.config.tip_product_id && line.product.id === this.pos.config.tip_product_id[0];
            //reward_id is always false unless the line is a reward from pos_loyalty
            return orderlines.filter((line) => !line.is_program_reward && !line.reward_id && !line.refunded_orderline_id && !is_gift_card_product(line) && !is_tips_product(line));
        },
        _getRewardLines: function () {
            const orderlines = _order_super.get_orderlines.apply(this, arguments);
            return orderlines.filter((line) => line.is_program_reward);
        },
        wait_for_push_order: function () {
            return (
                (this.programIdsToGenerateCoupons && this.programIdsToGenerateCoupons.length) ||
                this.get_orderlines().filter((line) => line.is_program_reward).length ||
                _order_super.wait_for_push_order.apply(this, arguments)
            );
        },
        export_for_printing: function () {
            let result = _order_super.export_for_printing.apply(this, arguments);
            result.generated_coupons = this.generated_coupons;
            return result;
        },
        add_product: async function (product, options) {
            await _order_super.add_product.apply(this, [product, options]);
            this.trigger('update-rewards');
        },
        get_last_orderline: function () {
            const regularLines = _order_super.get_orderlines
                .apply(this, arguments)
                .filter((line) => !line.is_program_reward);
            return regularLines[regularLines.length - 1];
        },
        selectLastOrderline: function(line){
            if(!line.is_program_reward) {
                _order_super.selectLastOrderline.apply(this, arguments);
            }
        },
        set_pricelist: function (pricelist) {
            _order_super.set_pricelist.apply(this, arguments);
            this.trigger('update-rewards');
        },

        // NEW METHODS

        _initializePrograms: async function () {
            if (!this.bookedCouponCodes) {
                /**
                 * This field contains the activated coupons.
                 * @type {Record<string, CouponCode>} key is the coupon code.
                 */
                this.bookedCouponCodes = {};
            }
            if (!(this.activePromoProgramIds && this.activePromoProgramIds.length)) {
                /**
                 * This field contains the ids of automatically/manually activated
                 * promo programs.
                 * @type {number[]} array of program ids.
                 */
                this.activePromoProgramIds = this._getAutomaticPromoProgramIds();
            }
        },
        resetPrograms: function () {
            let deactivatedCount = 0;
            if (this.bookedCouponCodes) {
                const couponIds = Object.values(this.bookedCouponCodes).map((couponCode) => couponCode.coupon_id);
                if (couponIds.length > 0) {
                    this.trigger('reset-coupons', couponIds);
                }
                this.bookedCouponCodes = {};
                deactivatedCount += couponIds.length;
            }
            if (this.activePromoProgramIds) {
                const codeNeededPromoProgramIds = this.activePromoProgramIds.filter((program_id) => {
                    return this.pos.coupon_programs_by_id[program_id].promo_code_usage === 'code_needed';
                });
                this.activePromoProgramIds = this._getAutomaticPromoProgramIds();
                deactivatedCount += codeNeededPromoProgramIds.length;
            }
            if (deactivatedCount > 0) Gui.showNotification('Active coupons and promo codes were deactivated.');
            this.trigger('update-rewards');
        },
        /**
         * Updates `bookedCouponCodes` or `activePromoProgramIds` depending on which code
         * is scanned.
         *
         * @param {string} code
         */
        activateCode: async function (code) {
            const promoProgram = this.pos.promo_programs.find(
                (program) => program.promo_barcode == code || program.promo_code == code
            );
            if (promoProgram && this.activePromoProgramIds.includes(promoProgram.id)) {
                Gui.showNotification('That promo code program has already been activated.');
            } else if (promoProgram) {
                // TODO these two operations should be atomic
                this.activePromoProgramIds.push(promoProgram.id);
                this.trigger('update-rewards');
            } else if (code in this.bookedCouponCodes) {
                Gui.showNotification('That coupon code has already been scanned and activated.');
            } else {
                const programIdsWithScannedCoupon = Object.values(this.bookedCouponCodes).map(
                    (couponCode) => couponCode.program_id
                );
                const customer = this.get_client();
                const { successful, payload } = await rpc.query({
                    model: 'pos.config',
                    method: 'use_coupon_code',
                    args: [
                        [this.pos.config.id],
                        code,
                        this.creation_date,
                        customer ? customer.id : false,
                        programIdsWithScannedCoupon,
                    ],
                    kwargs: { context: session.user_context },
                });
                if (successful) {
                    // TODO these two operations should be atomic
                    this.bookedCouponCodes[code] = new CouponCode(code, payload.coupon_id, payload.program_id);
                    this.trigger('update-rewards');
                } else {
                    Gui.showNotification(payload.error_message);
                }
            }
        },
        /**
         * @returns {[models.Orderline[], RewardsContainer]}
         */
        _getNewRewardLines: async function () {
            // Remove the reward lines before recalculation of rewards.
            this.orderlines.remove(this._getRewardLines());
            const rewardsContainer = await this._calculateRewards();
            // We set the programs that will generate coupons after validation of this order.
            // See `_postPushOrderResolve` in the `PaymentScreen`.
            await this._setProgramIdsToGenerateCoupons(rewardsContainer);
            // Create reward orderlines here based on the content of `rewardsContainer` field.
            return [this._getLinesToAdd(rewardsContainer), rewardsContainer];
        },
        /**
         * @param {number[]} couponIds ids of the coupon.coupon records to reset
         */
        resetCoupons: async function (couponIds) {
            await rpc.query(
                {
                    model: 'coupon.coupon',
                    method: 'write',
                    args: [couponIds, { state: 'new' }],
                    kwargs: { context: session.user_context },
                },
                {}
            );
        },
        /**
         * Create orderline rewards based on the `awarded` rewards from `rewardsContainer`.
         *
         * @param {RewardsContainer} rewardsContainer
         * @returns {models.Orderline[]}
         */
        _getLinesToAdd: function (rewardsContainer) {
            this.assert_editable();
            return rewardsContainer
                .getAwarded()
                .map(({ product, unit_price, quantity, program, tax_ids, coupon_id }) => {
                    let description;
                    /**
                     * Improved description only aplicable for rewards of type discount, and the discount is a percentage
                     * of the price, those are:
                     * - % discount on specific products.
                     * - % discount on the whole order.
                     * - % discount on the cheapest product.
                     */
                    if (tax_ids && program.reward_type === "discount" && program.discount_type === "percentage") {
                        description =
                            tax_ids.length > 0
                                ? _.str.sprintf(
                                    this.pos.env._t("Tax: %s"),
                                    tax_ids.map((tax_id) => `%${this.pos.taxes_by_id[tax_id].amount}`).join(", ")
                                )
                                : this.pos.env._t("No tax");
                    }
                    const options = {
                        description,
                        quantity: quantity,
                        price: unit_price,
                        lst_price: unit_price,
                        is_program_reward: true,
                        program_id: program.id,
                        tax_ids: tax_ids,
                        coupon_id: coupon_id,
                    };
                    const line = new models.Orderline({}, { pos: this.pos, order: this, product });
                    this.fix_tax_included_price(line);
                    this.set_orderline_options(line, options);
                    return line;
                });
        },
        /**
         * Sets the programs ids that will generate coupons based on the `rewardsContainer`.
         * If a program do not pass the rules-check, we add an 'unawarded' `Reward` in the
         * `rewardsContainer`.
         *
         * @param {RewardsContainer} rewardsContainer
         */
        _setProgramIdsToGenerateCoupons: async function (rewardsContainer) {
            const programIdsToGenerateCoupons = [];
            for (let [program] of this._getActiveOnNextPromoPrograms()) {
                const { successful, reason } = await this._checkProgramRules(program);
                if (successful) {
                    programIdsToGenerateCoupons.push(program.id);
                } else {
                    const notAwarded = new Reward({ program, reason, awarded: false });
                    rewardsContainer.add([notAwarded]);
                }
            }
            this.programIdsToGenerateCoupons = programIdsToGenerateCoupons;
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
        _calculateRewards: async function () {
            const rewardsContainer = new RewardsContainer();

            if (this._getRegularOrderlines().length === 0) {
                return rewardsContainer;
            }

            const {
                freeProductPrograms,
                fixedAmountDiscountPrograms,
                onSpecificPrograms,
                onCheapestPrograms,
                onOrderPrograms,
            } = await this._getValidActivePrograms(rewardsContainer);

            const collectRewards = (validPrograms, rewardGetter) => {
                const allRewards = [];
                for (let [program, coupon_id] of validPrograms) {
                    const [rewards, reason] = rewardGetter(program, coupon_id);
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
            const specificDiscountGetter = (program, coupon_id) => {
                return this._getSpecificDiscount(program, coupon_id, freeProducts);
            };
            const specificDiscounts = collectRewards(onSpecificPrograms, specificDiscountGetter);

            // - Collect the discounts from on order and on cheapest discount programs.
            const globalDiscounts = [];
            const onOrderDiscountGetter = (program, coupon_id) => {
                return this._getOnOrderDiscountRewards(program, coupon_id, freeProducts);
            };
            globalDiscounts.push(...collectRewards(onOrderPrograms, onOrderDiscountGetter));
            globalDiscounts.push(...collectRewards(onCheapestPrograms, (program, coupon_id) => this._getOnCheapestProductDiscount(program, coupon_id, freeProducts)));

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
        _getValidActivePrograms: async function (rewardsContainer) {
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

            for (let [program, coupon_id] of this._getBookedPromoPrograms()) {
                // Booked coupons from on next order promo programs do not need
                // checking of rules because checks are done before generating
                // coupons.
                updateProgramLists(program, coupon_id);
            }

            for (let [program, coupon_id] of [
                ...this._getBookedCouponPrograms(),
                ...this._getActiveOnCurrentPromoPrograms(),
            ]) {
                const { successful, reason } = await this._checkProgramRules(program);
                if (successful) {
                    updateProgramLists(program, coupon_id);
                } else {
                    // side-effect
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
        _getAutomaticPromoProgramIds: function () {
            return this.pos.promo_programs
                .filter((program) => {
                    return program.promo_code_usage == 'no_code_needed';
                })
                .map((program) => program.id);
        },
        /**
         * These are the coupon programs that are activated
         * via coupon codes. RewardsContainer can only be generated if the coupon
         * program rules are satisfied.
         *
         * @returns {[coupon.program, number][]}
         */
        _getBookedCouponPrograms: function () {
            return Object.values(this.bookedCouponCodes)
                .map((couponCode) => [
                    this.pos.coupon_programs_by_id[couponCode.program_id],
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
        _getBookedPromoPrograms: function () {
            return Object.values(this.bookedCouponCodes)
                .map((couponCode) => [
                    this.pos.coupon_programs_by_id[couponCode.program_id],
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
        _getActiveOnCurrentPromoPrograms: function () {
            return this.activePromoProgramIds
                .map((program_id) => [this.pos.coupon_programs_by_id[program_id], null])
                .filter(([program]) => {
                    return program.promo_applicability === 'on_current_order';
                });
        },
        /**
         * These are the active on_next_order promo programs that will generate
         * coupon codes if the program constraints are fully-satisfied.
         *
         * @returns {[coupon.program, null][]}
         */
        _getActiveOnNextPromoPrograms: function () {
            return this.activePromoProgramIds
                .map((program_id) => [this.pos.coupon_programs_by_id[program_id], null])
                .filter(([program]) => {
                    return program.promo_applicability === 'on_next_order';
                });
        },
        _convertToDate: function (stringDate) {
            return new Date(stringDate.replace(/ /g, 'T').concat('Z'))
        },
        /**
         * @param {coupon.program} program
         * @returns {{ successful: boolean, reason: string | undefined }}
         */
        _checkProgramRules: async function (program) {
            // Check minimum amount
            const amountToCheck =
                program.rule_minimum_amount_tax_inclusion === 'tax_included'
                    ? this.get_total_with_tax()
                    : this.get_total_without_tax();
            // TODO jcb rule_minimum_amount has to be converted.
            if (
                !(
                    amountToCheck > program.rule_minimum_amount ||
                    float_is_zero(amountToCheck - program.rule_minimum_amount, this.pos.currency.decimals)
                )
            ) {
                return {
                    successful: false,
                    reason: 'Minimum amount for this program is not satisfied.',
                };
            }

            // Check minimum quantity
            const validQuantity = this._getRegularOrderlines()
                .filter((line) => {
                    return program.valid_product_ids.has(line.product.id);
                })
                .reduce((total, line) => total + line.quantity, 0);
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
            const customer = this.get_client();
            const partnersDomain = program.rule_partners_domain || '[]';
            if (partnersDomain !== '[]' && !program.valid_partner_ids.has(customer ? customer.id : 0)) {
                return {
                    successful: false,
                    reason: "Current customer can't avail this program.",
                };
            }

            // Check rule date
            const ruleFrom = program.rule_date_from ? this._convertToDate(program.rule_date_from) : new Date(-8640000000000000);
            const ruleTo = program.rule_date_to ? this._convertToDate(program.rule_date_to) : new Date(8640000000000000);
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
         * This method is called via `collectRewards` inside `_calculateRewards`.
         * The purpose of this method is to create `Reward` objects based on the given
         * `program` and `coupon_id`.
         * It returns a tuple of rewards and reason if no rewards are created.
         *
         * @param {coupon.program} program
         * @param {number} coupon_id
         * @returns {[Reward[], string | null]}
         */
        _getProductRewards: function (program, coupon_id) {
            const rewardProduct = this.pos.db.get_product_by_id(program.reward_product_id[0]);
            const countedOrderlines = this._getRegularOrderlines().filter((line) =>
                program.valid_product_ids.has(line.product.id)
            );
            const totalQuantity = countedOrderlines.reduce((quantity, line) => quantity + line.quantity, 0);
            const totalAmount = countedOrderlines.reduce((amount, line) => {
                const { priceWithTax, priceWithoutTax } = line.get_all_prices();
                if (program.rule_minimum_amount_tax_inclusion == 'tax_included') {
                    amount += priceWithTax;
                } else {
                    amount += priceWithoutTax;
                }
                return amount;
            }, 0);

            // Compute the free quantities based on rule_min_amount and rule_min_quantity.
            let freeQuantityFromMinAmount = Math.Infinity;
            let freeQuantityFromMinQuantity;
            const existingRewardQty = this._getRegularOrderlines()
                .filter((line) => line.product.id == rewardProduct.id)
                .reduce((total, line) => total + line.quantity, 0);
            if (program.valid_product_ids.has(rewardProduct.id)) {
                if (existingRewardQty) {
                    freeQuantityFromMinQuantity = Math.min(
                        computeFreeQuantity(totalQuantity, program.rule_min_quantity, program.reward_product_quantity),
                        existingRewardQty
                    );
                    if (program.rule_minimum_amount !== 0) {
                        // Normalize the values based on amount to be able to utilize computeFreeQuantity.
                        const rewardProductAmount = program.reward_product_quantity * rewardProduct.lst_price;
                        const freeAmount = computeFreeQuantity(
                            totalAmount,
                            program.rule_minimum_amount,
                            rewardProductAmount
                        );
                        freeQuantityFromMinAmount = Math.min(
                            Math.trunc(freeAmount / rewardProduct.lst_price),
                            existingRewardQty
                        );
                    }
                } else {
                    // No free quantity if the reward product is not among the orderlines.
                    freeQuantityFromMinQuantity = 0;
                    freeQuantityFromMinAmount = 0;
                }
            } else {
                freeQuantityFromMinQuantity = Math.min(
                    Math.trunc((totalQuantity * program.reward_product_quantity) / program.rule_min_quantity),
                    existingRewardQty
                );
                if (program.rule_minimum_amount !== 0) {
                    freeQuantityFromMinAmount = Math.min(
                        Math.trunc((totalAmount * program.reward_product_quantity) / program.rule_minimum_amount),
                        existingRewardQty
                    );
                }
            }

            // Based on freeQuantityFromMinAmount and freeQuantityFromMinQuantity, compute the actual free quantity.
            let freeQuantity = 0;
            if (freeQuantityFromMinAmount < freeQuantityFromMinQuantity) {
                freeQuantity = freeQuantityFromMinAmount;
            } else {
                freeQuantity = freeQuantityFromMinQuantity;
            }

            if (freeQuantity === 0) {
                return [[], 'Zero free product quantity.'];
            } else {
                const discountLineProduct = this.pos.db.get_product_by_id(program.discount_line_product_id[0]);
                return [
                    [
                        new Reward({
                            product: discountLineProduct,
                            unit_price: -round_decimals(rewardProduct.get_price(this.pricelist, freeQuantity), this.pos.currency.decimals),
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
        _getFixedDiscount: function (program, coupon_id) {
            const discountAmount = Math.min(program.discount_fixed_amount, program.discount_max_amount || Infinity);
            return [
                [
                    new Reward({
                        product: this.pos.db.get_product_by_id(program.discount_line_product_id[0]),
                        unit_price: -discountAmount,
                        quantity: 1,
                        program: program,
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
        _getSpecificDiscount: function (program, coupon_id, productRewards) {
            const productIdsToAccount = new Set();
            const amountsToDiscount = {};
            for (let line of this._getRegularOrderlines()) {
                if (program.discount_specific_product_ids.has(line.get_product().id)) {
                    const key = this._getGroupKey(line);
                    if (!(key in amountsToDiscount)) {
                        amountsToDiscount[key] = line.get_base_price();
                    } else {
                        amountsToDiscount[key] += line.get_base_price();
                    }
                    productIdsToAccount.add(line.get_product().id);
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
        _getOnCheapestProductDiscount: function (program, coupon_id, productRewards) {
            const amountsToDiscount = {};
            const orderlines = this._getRegularOrderlines();
            if (orderlines.length > 0) {
                const cheapestLine = this._findCheapestLine(orderlines, productRewards);
                if (cheapestLine) {
                    const key = this._getGroupKey(cheapestLine);
                    amountsToDiscount[key] = cheapestLine.price;
                }
            }
            return this._createDiscountRewards(program, coupon_id, amountsToDiscount);
        },
        /**
         * Returns the cheapest line from the given orderlines considering the rewarded products.
         * @param {models.Orderline[]} orderlines
         * @param {Reward[]} productRewards
         * @returns {models.Orderline}
         */
        _findCheapestLine: function (orderlines, productRewards) {
            // Compute free quantity per product.
            const freeQuantityPerProduct = {};
            for (const productReward of productRewards) {
                const productId = productReward.rewardedProductId;
                if (!(productId in freeQuantityPerProduct)) {
                    freeQuantityPerProduct[productId] = 0;
                }
                freeQuantityPerProduct[productId] += productReward.quantity;
            }
            // Map each line to its remaining free quantity.
            // Important to loop over the lines in decreasing price.
            const remainingQtyOfLine = new Map();
            for (const line of [...orderlines].sort((a, b) => b.price - a.price)) {
                const productId = line.product.id;
                let freeQuantity = freeQuantityPerProduct[productId] || 0;
                remainingQtyOfLine.set(line, line.get_quantity());
                if (float_is_zero(freeQuantity, this.pos.dp['Product Unit of Measure'])) {
                    continue;
                }
                const lineQty = remainingQtyOfLine.get(line);
                if (lineQty < freeQuantity) {
                    remainingQtyOfLine.set(line, 0);
                    freeQuantity -= lineQty;
                } else {
                    remainingQtyOfLine.set(line, lineQty - freeQuantity);
                    freeQuantity = 0;
                }
                freeQuantityPerProduct[productId] = freeQuantity;
            }
            // Among the lines with remaining quantity, return the one with the lowest price.
            const linesWithoutRewards = [...remainingQtyOfLine.entries()]
                .filter(([_, remainingQty]) => !float_is_zero(remainingQty, this.pos.currency.decimals))
                .map(([line, _]) => line)
                .sort((a, b) => a.price - b.price);
            return linesWithoutRewards[0];
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
        _getOnOrderDiscountRewards: function (program, coupon_id, productRewards) {
            const productIdsToAccount = new Set();
            const amountsToDiscount = {};
            for (let line of this._getRegularOrderlines()) {
                const key = this._getGroupKey(line);
                if (!(key in amountsToDiscount)) {
                    amountsToDiscount[key] = line.get_base_price();
                } else {
                    amountsToDiscount[key] += line.get_base_price();
                }
                productIdsToAccount.add(line.get_product().id);
            }
            this._considerProductRewards(amountsToDiscount, productIdsToAccount, productRewards);
            return this._createDiscountRewards(program, coupon_id, amountsToDiscount);
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
            //Remove entries from amountsToDiscount that are 0
            for (let key in amountsToDiscount) {
                if (amountsToDiscount[key] === 0) {
                    delete amountsToDiscount[key];
                }
            }
        },
        _getGroupKey: function (line) {
            return line
                .get_taxes()
                .map((tax) => tax.id)
                .join(',');
        },
        _createDiscountRewards: function (program, coupon_id, amountsToDiscount) {
            const rewards = [];
            const totalAmountsToDiscount = Object.values(amountsToDiscount).reduce((a, b) => a + b, 0);
            for (let [tax_keys, amount] of Object.entries(amountsToDiscount)) {
                let discountAmount = (amount * program.discount_percentage) / 100.0;
                let maxDiscount = amount / totalAmountsToDiscount * (program.discount_max_amount || Infinity);
                discountAmount = Math.min(discountAmount, maxDiscount);
                rewards.push(new Reward({
                    product: this.pos.db.get_product_by_id(program.discount_line_product_id[0]),
                    unit_price: -discountAmount,
                    quantity: 1,
                    program: program,
                    tax_ids: tax_keys !== '' ? tax_keys.split(',').map((val) => parseInt(val, 10)) : [],
                    coupon_id: coupon_id,
                }));
            }
            return [rewards, rewards.length > 0 ? null : 'No items to discount.'];
        }
    });

    var _orderline_super = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        export_as_JSON: function () {
            var result = _orderline_super.export_as_JSON.apply(this);
            result.is_program_reward = this.is_program_reward;
            result.program_id = this.program_id;
            result.coupon_id = this.coupon_id;
            return result;
        },
        init_from_JSON: function (json) {
            if (json.is_program_reward) {
                this.is_program_reward = json.is_program_reward;
                this.program_id = json.program_id;
                this.coupon_id = json.coupon_id;
                if (this.coupon_id && this.coupon_id[1]) {
                    this.order.bookedCouponCodes[this.coupon_id[1]] = new CouponCode(this.coupon_id[1], this.coupon_id[0], this.program_id);
                    this.coupon_id = json.coupon_id[0];
                } else if (json.program_id && this.order.activePromoProgramIds.indexOf(json.program_id) === -1) {
                    this.order.activePromoProgramIds.push(json.program_id);
                }
            }
            _orderline_super.init_from_JSON.apply(this, [json]);
        },
        set_quantity: function (quantity, keep_price) {
            const result = _orderline_super.set_quantity.apply(this, [quantity, keep_price]);
            // This function removes an order line if we set the quantity to 'remove'
            // We extend its functionality so that if a reward line is removed,
            // other reward lines from the same program are also deleted.
            if (quantity === 'remove' && this.is_program_reward) {
                let related_rewards = this.order.orderlines.filter(
                    (line) => line.is_program_reward && line.program_id === this.program_id
                );
                for (let line of related_rewards) {
                    line.order.remove_orderline(line);
                }
                if (related_rewards.length !== 0) {
                    Gui.showNotification('Other reward lines from the same program were also removed.');
                }
            }
            return result;
        },
    });

    return {CouponCode, RewardsContainer, Reward};
});
