import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
    _getEWalletRewards(order) {
        const claimableRewards = order.getClaimableRewards();
        return claimableRewards.filter((reward_line) => {
            const coupon = this.pos.models["loyalty.card"].get(reward_line.coupon_id);
            return (
                coupon &&
                reward_line.reward.program_id.program_type == "ewallet" &&
                !coupon.isExpired()
            );
        });
    },
    _getEWalletPrograms() {
        return this.pos.models["loyalty.program"].filter((p) => p.program_type == "ewallet");
    },
    async onClickWallet() {
        const order = this.pos.get_order();
        const eWalletPrograms = this._getEWalletPrograms();
        const orderTotal = order.get_total_with_tax();
        const eWalletRewards = this._getEWalletRewards(order);
        if (eWalletRewards.length === 0 && orderTotal >= 0) {
            this.dialog.add(AlertDialog, {
                title: _t("No valid eWallet found"),
                body: _t(
                    "You either have not created an eWallet or all your eWallets have expired."
                ),
            });
            return;
        }
        if (orderTotal < 0 && eWalletPrograms.length >= 1) {
            let selectedProgram = null;
            if (eWalletPrograms.length == 1) {
                selectedProgram = eWalletPrograms[0];
            } else {
                selectedProgram = await makeAwaitable(this.dialog, SelectionPopup, {
                    title: _t("Refund with eWallet"),
                    list: eWalletPrograms.map((program) => ({
                        id: program.id,
                        item: program,
                        label: program.name,
                    })),
                });
            }
            if (selectedProgram) {
                this.pos.addLineToCurrentOrder(
                    {
                        product_id: selectedProgram.trigger_product_ids[0],
                        _e_wallet_program_id: selectedProgram,
                        price_unit: -orderTotal,
                    },
                    {}
                );
            }
        } else if (eWalletRewards.length >= 1) {
            let eWalletReward = null;
            if (eWalletRewards.length == 1) {
                eWalletReward = eWalletRewards[0];
            } else {
                eWalletReward = await makeAwaitable(this.dialog, SelectionPopup, {
                    title: _t("Use eWallet to pay"),
                    list: eWalletRewards.map(({ reward, coupon_id }) => ({
                        id: reward.id,
                        item: { reward, coupon_id },
                        label: `${reward.description} (${reward.program_id.name})`,
                    })),
                });
            }
            if (eWalletReward) {
                const result = order._applyReward(
                    eWalletReward.reward,
                    eWalletReward.coupon_id,
                    {}
                );
                if (result !== true) {
                    // Returned an error
                    this.dialog.add(AlertDialog, {
                        title: _t("Error"),
                        body: result,
                    });
                }
                this.pos.updateRewards();
            }
        }
    },
    async clickPromoCode() {
        this.dialog.add(TextInputPopup, {
            title: _t("Enter Code"),
            placeholder: _t("Gift card or Discount code"),
            getPayload: async (code) => {
                code = code.trim();
                if (code !== "") {
                    const res = await this.pos.activateCode(code);
                    if (res !== true) {
                        this.notification.add(res, { type: "danger" });
                    }
                }
            },
        });
    },

    getPotentialRewards() {
        const order = this.pos.get_order();
        // Claimable rewards excluding those from eWallet programs.
        // eWallet rewards are handled in the eWalletButton.
        let rewards = [];
        if (order) {
            const claimableRewards = order.getClaimableRewards();
            rewards = claimableRewards.filter(
                ({ reward }) => reward.program_id.program_type !== "ewallet"
            );
        }
        const result = {};
        const discountRewards = rewards.filter(({ reward }) => reward.reward_type == "discount");
        const freeProductRewards = rewards.filter(({ reward }) => reward.reward_type == "product");
        const potentialFreeProductRewards = this.pos.getPotentialFreeProductRewards();
        const avaiRewards = [
            ...potentialFreeProductRewards,
            ...discountRewards,
            ...freeProductRewards, // Free product rewards at the end of array to prioritize them
        ];

        for (const reward of avaiRewards) {
            result[reward.reward.id] = reward;
        }

        return Object.values(result);
    },

    /**
     * Applies the reward on the current order, if multiple products can be claimed opens a popup asking for which one.
     *
     * @param {Object} reward
     * @param {Integer} coupon_id
     */
    async _applyReward(reward, coupon_id, potentialQty) {
        const order = this.pos.get_order();
        order.uiState.disabledRewards.delete(reward.id);

        const args = {};
        if (reward.reward_type === "product" && reward.multi_product) {
            const productsList = reward.reward_product_ids.map((product_id) => ({
                id: product_id.id,
                label: product_id.display_name,
                item: product_id,
            }));
            const selectedProduct = await makeAwaitable(this.dialog, SelectionPopup, {
                title: _t("Please select a product for this reward"),
                list: productsList,
            });
            if (!selectedProduct) {
                return false;
            }
            args["product"] = selectedProduct;
        }
        if (
            (reward.reward_type == "product" && reward.program_id.applies_on !== "both") ||
            (reward.program_id.applies_on == "both" && potentialQty)
        ) {
            await this.pos.addLineToCurrentOrder(
                {
                    product_id: args["product"] || reward.reward_product_ids[0],
                    qty: potentialQty || 1,
                },
                {}
            );
            return true;
        } else {
            const result = order._applyReward(reward, coupon_id, args);
            if (result !== true) {
                // Returned an error
                this.notification.add(result);
            }
            this.pos.updateRewards();
            return result;
        }
    },
    async clickRewards() {
        const rewards = this.getPotentialRewards();
        if (rewards.length >= 1) {
            const rewardsList = rewards.map((reward) => ({
                id: reward.reward.id,
                label: reward.reward.program_id.name,
                description: `Add "${reward.reward.description}"`,
                item: reward,
            }));
            this.dialog.add(SelectionPopup, {
                title: _t("Available rewards"),
                list: rewardsList,
                getPayload: (selectedReward) => {
                    this._applyReward(
                        selectedReward.reward,
                        selectedReward.coupon_id,
                        selectedReward.potentialQty
                    );
                },
            });
        }
    },
});
