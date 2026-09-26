import { computed, usePlugin } from "@odoo/owl";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { PosNumberBufferPlugin } from "@point_of_sale/app/plugins/pos_number_buffer_plugin";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.numberBuffer = usePlugin(PosNumberBufferPlugin);
        this.nbrRewards = computed(() => this.getPotentialRewards().length);
    },
    _getEWalletRewards(order) {
        const appliedRewardIds = new Set(
            order.active_payment_programs.map((entry) => entry.reward_id)
        );
        const rewards = [];
        for (const program of this._getEWalletPrograms()) {
            const reward = program.reward_ids[0];
            if (appliedRewardIds.has(reward.id)) {
                // Already applied to this order: don't offer it again.
                continue;
            }
            const card = this.pos.models["loyalty.card"].find(
                (card) =>
                    card.program_id?.id === program.id &&
                    card.partner_id?.id === order.partner_id?.id &&
                    !card.isExpired() &&
                    card.points > 0
            );
            if (card) {
                rewards.push({ reward, card_id: card.id });
            }
        }
        return rewards;
    },
    _getEWalletPrograms() {
        return this.pos.models["loyalty.program"].filter((p) => p.program_type == "ewallet");
    },
    async onClickWalletRefund() {
        const order = this.pos.getOrder();
        const eWalletPrograms = this._getEWalletPrograms();
        const orderTotal = order.priceIncl;
        if (eWalletPrograms.length === 0) {
            this.dialog.add(AlertDialog, {
                title: _t("No valid eWallet found"),
                body: _t("Please select a customer and a valid eWallet."),
            });
            return;
        }
        let program = eWalletPrograms[0];
        if (eWalletPrograms.length > 1) {
            program = await makeAwaitable(this.dialog, SelectionPopup, {
                title: _t("Refund with eWallet"),
                list: eWalletPrograms.map((p) => ({ id: p.id, item: p, label: p.name })),
            });
            if (!program) {
                return;
            }
        }
        const triggerProducts = program.trigger_product_ids.filter(
            (product) => product.product_tmpl_id?.canBeDisplayed
        );
        if (triggerProducts.length === 0) {
            this.dialog.add(AlertDialog, {
                title: _t("No valid eWallet found"),
                body: _t("This eWallet has no product available to refund to."),
            });
            return;
        }
        let triggerProduct = triggerProducts[0];
        if (triggerProducts.length > 1) {
            triggerProduct = await makeAwaitable(this.dialog, SelectionPopup, {
                title: _t("Select a product"),
                list: triggerProducts.map((product) => ({
                    id: product.id,
                    item: product,
                    label: product.display_name,
                })),
            });
            if (!triggerProduct) {
                return;
            }
        }
        await this.pos.addLineToCurrentOrder(
            {
                product_id: triggerProduct,
                product_tmpl_id: triggerProduct.product_tmpl_id,
                qty: 1,
                price_unit: -orderTotal,
            },
            { paymentProgram: program }
        );
    },
    async onClickWalletPay() {
        const order = this.pos.getOrder();
        const eWalletRewards = this._getEWalletRewards(order);
        if (eWalletRewards.length === 0) {
            this.dialog.add(AlertDialog, {
                title: _t("No valid eWallet found"),
                body: _t("Please select a customer and a valid eWallet."),
            });
            return;
        }
        let eWalletReward = null;
        if (eWalletRewards.length == 1) {
            eWalletReward = eWalletRewards[0];
        } else {
            eWalletReward = await makeAwaitable(this.dialog, SelectionPopup, {
                title: _t("Use eWallet to pay"),
                list: eWalletRewards.map(({ reward, card_id }) => ({
                    id: reward.id,
                    item: { reward, card_id },
                    label: `${reward.description} (${reward.program_id.name})`,
                })),
            });
        }
        if (eWalletReward) {
            // Activate the eWallet by its card code: applyCode routes payment programs
            // into active_payment_programs, which recomputeRewards spends via
            // applyPaymentProgram.
            const card = this.pos.models["loyalty.card"].get(eWalletReward.card_id);
            await this.pos.applyCode(card.code);
            this.pos.updateRewards();
        }
    },
    async clickPromoCode() {
        const order = this.pos.getOrder();
        this.dialog.add(TextInputPopup, {
            title: _t("Enter Code"),
            placeholder: _t("Gift card or Discount code"),
            size: "md",
            removeNewLines: true,
            getPayload: async (code) => {
                code = code.trim();
                if (code === "") {
                    return;
                }
                const loadError = await this.pos.loadCode(code);
                if (loadError) {
                    this.notification.add(loadError, { type: "danger" });
                    return;
                }
                await this.pos.applyCode(code);
                order.recomputeRewards();
            },
        });
    },

    getPotentialRewards() {
        const order = this.pos.getOrder();
        // Claimable rewards excluding those from eWallet programs.
        // eWallet rewards are handled in the eWalletButton.
        let rewards = [];
        if (order) {
            const claimableRewards = order.availableRewards;
            rewards = claimableRewards.filter(
                (reward) => reward.reward.program_id.program_type !== "ewallet"
            );
        }
        const result = {};
        const discountRewards = rewards.filter((reward) => reward.reward.reward_type == "discount");
        const freeProductRewards = rewards.filter(
            (reward) => reward.reward.reward_type == "product"
        );
        const avaiRewards = [
            ...discountRewards,
            ...freeProductRewards, // Free product rewards at the end of array to prioritize them
        ];

        for (const reward of avaiRewards) {
            result[reward.reward.id] = reward;
        }

        return Object.values(result);
    },
    async clickRewards() {
        const order = this.pos.getOrder();
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
                getPayload: async (selectedReward) => {
                    const reward = selectedReward.reward;
                    const programId = reward.program_id?.id;
                    if (order.disabled_program_ids.includes(programId)) {
                        order.disabled_program_ids = order.disabled_program_ids.filter(
                            (id) => id !== programId
                        );
                        if (order.appliedPrograms.some((program) => program.id === programId)) {
                            order.recomputeRewards();
                            if (order._selectRewardLine(reward)) {
                                this.numberBuffer.reset();
                            }
                            return;
                        }
                    }

                    let reward_product_id;

                    if (reward.multi_product) {
                        reward_product_id = await makeAwaitable(this.dialog, SelectionPopup, {
                            title: _t("Please select a product for this reward"),
                            list: reward.reward_product_ids.map((product) => ({
                                id: product.id,
                                item: product,
                                label: product.display_name,
                            })),
                        });
                        if (!reward_product_id) {
                            return;
                        }
                    }

                    const product =
                        reward_product_id ||
                        reward.reward_product_id ||
                        reward.reward_product_ids[0];
                    let attribute_value_ids = [];
                    let attribute_custom_values = [];
                    if (
                        reward.reward_type == "product" &&
                        product.product_tmpl_id.isConfigurable()
                    ) {
                        const attributeValues = await this.pos.openConfigurator(
                            product.product_tmpl_id,
                            {
                                presetVariant: product,
                            }
                        );
                        if (!attributeValues) {
                            return;
                        }
                        attribute_value_ids = attributeValues.attribute_value_ids;
                        attribute_custom_values = attributeValues.attribute_custom_values;
                    }

                    order.active_rewards.push({
                        reward_id: reward.id,
                        reward_product_id,
                        attribute_value_ids,
                        attribute_custom_values,
                    });
                    order.recomputeRewards();
                    if (order._selectRewardLine(reward)) {
                        this.numberBuffer.reset();
                    }
                },
            });
        }
    },
});
