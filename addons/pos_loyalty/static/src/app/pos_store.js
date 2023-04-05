/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/pos_store";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/js/Popups/SelectionPopup";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import { TextInputPopup } from "@point_of_sale/js/Popups/TextInputPopup";

patch(PosStore.prototype, "pos_loyalty.PosStore", {
    async addProductFromUi(product, options) {
        const _super = this._super;
        const order = this.globalState.get_order();
        const linkedProgramIds = this.globalState.productId2ProgramIds[product.id] || [];
        const linkedPrograms = linkedProgramIds.map((id) => this.globalState.program_by_id[id]);
        let selectedProgram = null;
        if (linkedPrograms.length > 1) {
            const { confirmed, payload: program } = await this.popup.add(SelectionPopup, {
                title: _t("Select program"),
                list: linkedPrograms.map((program) => ({
                    id: program.id,
                    item: program,
                    label: program.name,
                })),
            });
            if (confirmed) {
                selectedProgram = program;
            } else {
                // Do nothing here if the selection is cancelled.
                return;
            }
        } else if (linkedPrograms.length === 1) {
            selectedProgram = linkedPrograms[0];
        }
        const orderTotal = this.globalState.get_order().get_total_with_tax();
        if (
            selectedProgram &&
            ["gift_card", "ewallet"].includes(selectedProgram.program_type) &&
            orderTotal < 0
        ) {
            options.price = -orderTotal;
        }
        if (selectedProgram && selectedProgram.program_type == "gift_card") {
            const shouldProceed = await this._setupGiftCardOptions(selectedProgram, options);
            if (!shouldProceed) {
                return;
            }
        } else if (selectedProgram && selectedProgram.program_type == "ewallet") {
            const shouldProceed = await this.setupEWalletOptions(selectedProgram, options);
            if (!shouldProceed) {
                return;
            }
        }
        const potentialRewards = this.getPotentialFreeProductRewards();
        const rewardsToApply = [];
        for (const reward of potentialRewards) {
            for (const reward_product_id of reward.reward.reward_product_ids) {
                if (reward_product_id == product.id) {
                    rewardsToApply.push(reward);
                }
            }
        }
        await _super(product, options);
        await order._updatePrograms();
        if (rewardsToApply.length == 1) {
            const reward = rewardsToApply[0];
            order._applyReward(reward.reward, reward.coupon_id, { product: product.id });
        }

        order._updateRewards();
        return options;
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
        if (this.globalState.config.gift_card_settings == "scan_use") {
            const { confirmed, payload: code } = await this.globalState.env.services.popup.add(
                TextInputPopup,
                {
                    title: _t("Generate a Gift Card"),
                    startingValue: "",
                    placeholder: _t("Enter the gift card code"),
                }
            );
            if (!confirmed) {
                return false;
            }
            const trimmedCode = code.trim();
            if (trimmedCode && trimmedCode.startsWith("044")) {
                // check if the code exist in the database
                // if so, use its balance, otherwise, use the unit price of the gift card product
                const fetchedGiftCard = await this.orm.searchRead(
                    "loyalty.card",
                    [
                        ["code", "=", trimmedCode],
                        ["program_id", "=", program.id],
                    ],
                    ["points", "source_pos_order_id"]
                );
                // There should be maximum one gift card for a given code.
                const giftCard = fetchedGiftCard[0];
                if (giftCard && giftCard.source_pos_order_id) {
                    this.popup.add(ErrorPopup, {
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
                    options.price = giftCard.points;
                    options.giftCardId = giftCard.id;
                }
            } else {
                this.globalState.env.services.pos_notification.add(
                    "Please enter a valid gift card code."
                );
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
    getPotentialFreeProductRewards() {
        const order = this.globalState.get_order();
        const allCouponPrograms = Object.values(order.couponPointChanges)
            .map((pe) => {
                return {
                    program_id: pe.program_id,
                    coupon_id: pe.coupon_id,
                };
            })
            .concat(
                order.codeActivatedCoupons.map((coupon) => {
                    return {
                        program_id: coupon.program_id,
                        coupon_id: coupon.id,
                    };
                })
            );
        const result = [];
        for (const couponProgram of allCouponPrograms) {
            const program = this.globalState.program_by_id[couponProgram.program_id];
            const points = order._getRealCouponPoints(couponProgram.coupon_id);
            const hasLine = order.orderlines.filter((line) => !line.is_reward_line).length > 0;
            for (const reward of program.rewards.filter(
                (reward) => reward.reward_type == "product"
            )) {
                if (points < reward.required_points) {
                    continue;
                }
                // Loyalty program (applies_on == 'both') should needs an orderline before it can apply a reward.
                const considerTheReward =
                    program.applies_on !== "both" || (program.applies_on == "both" && hasLine);
                if (reward.reward_type === "product" && considerTheReward) {
                    const product = this.globalState.db.get_product_by_id(
                        reward.reward_product_ids[0]
                    );
                    const potentialQty = order._computePotentialFreeProductQty(
                        reward,
                        product,
                        points
                    );
                    if (potentialQty <= 0) {
                        continue;
                    }
                    result.push({
                        coupon_id: couponProgram.coupon_id,
                        reward: reward,
                        potentialQty,
                    });
                }
            }
        }
        return result;
    },
});
