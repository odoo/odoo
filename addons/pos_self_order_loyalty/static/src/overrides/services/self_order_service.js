import { SelfOrder } from "@pos_self_order/app/services/self_order_service";
import { patch } from "@web/core/utils/patch";
import { InvalidDomainError } from "@web/core/domain";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { SelectProductPopup } from "@pos_self_order_loyalty/app/components/popup/select_product_popup/select_product_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { SelectRewardPopup } from "@pos_self_order_loyalty/app/components/popup/select_reward_popup/select_reward_popup";
import { UserInputPopup } from "@pos_self_order_loyalty/app/components/popup/user_input_popup/user_input_popup";
import { SelectAttributePopup } from "@pos_self_order_loyalty/app/components/popup/select_attribute_popup/select_attribute_popup";
import { isValidEmail } from "@point_of_sale/utils";

patch(SelfOrder.prototype, {
    createNewOrder() {
        const order = super.createNewOrder();
        if (this.config.self_ordering_mode == "mobile") {
            const partner = this.models["res.partner"].getFirst();
            if (partner) {
                order.setPartner(partner);
            }
        }
        return order;
    },
    async afterProcessServerData() {
        // Remove reward lines that have no reward anymore (could happen if the program got archived)
        this.models["pos.order.line"]
            .filter((order) => order.is_reward_line && !order.reward_id)
            .forEach((line) => line.delete());
        await super.afterProcessServerData(...arguments);
        this._checkRewardDomains();
    },
    /**
     * A discount reward may ship a `reward_product_domain` to be evaluated client-side
     * against loaded products. If the domain references a field the POS client doesn't
     * have (e.g. a non-`product.product` field), it can't be evaluated here. Warn and
     * drop such a reward at load, so it doesn't crash the order when it would apply.
     */
    _checkRewardDomains() {
        for (const reward of this.models["loyalty.reward"].filter(
            (reward) => reward.reward_type === "discount"
        )) {
            try {
                reward.getDiscountProductIds();
            } catch (error) {
                if (!(error instanceof InvalidDomainError || error instanceof TypeError)) {
                    throw error;
                }
                this.dialog.add(AlertDialog, {
                    title: _t("A reward could not be loaded"),
                    body: _t(
                        'The reward "%s" contains an error in its domain, your domain must be compatible with the PoS client',
                        reward.description
                    ),
                });
                reward.delete();
            }
        }
    },
    async initMobileData() {
        // If we load an existing order with synced reward lines, they will be updated. If we load an existing order without
        // synced reward lines. If we keep them, we can create duplicate reward lines when loading an existing order.
        this.models["pos.order.line"]
            .filter((line) => line.is_reward_line && !line.isSynced)
            .forEach((line) => {
                line.delete();
            });
        return super.initMobileData(...arguments);
    },
    _isSnapshotLine(line) {
        // Reward lines are derived from the order by recomputeRewards, they're not a server-side change
        return super._isSnapshotLine(...arguments) && !line.is_reward_line;
    },
    async canProceedToPay() {
        const canProceed = await super.canProceedToPay(...arguments);
        if (canProceed) {
            // The refresh brings back the synced reward lines already replaced locally, rebuild
            // them so that their removal is sent to the server instead of being duplicated
            this.currentOrder.recomputeRewards();
        }
        return canProceed;
    },
    deleteUnrelatedData() {
        // Theses cards can either be found again by a request to the server, either be recreated if needed by the js.
        const cardsToRemove = this.models["loyalty.card"].filter((card) =>
            [
                "coupons",
                "promo_code",
                "gift_card",
                "promotion",
                "buy_x_get_y",
                "next_order_coupons",
            ].includes(card.program_id.program_type)
        );
        // Remove all programs and related stuff linked to codes
        const programToRemove = this.models["loyalty.program"].filter((program) =>
            ["coupons", "promo_code", "next_order_coupons"].includes(program.program_type)
        );
        const programToRemoveIds = programToRemove.map((p) => p.id);
        const rulesToRemove = this.models["loyalty.rule"].filter((rule) =>
            programToRemoveIds.includes(rule.program_id.id)
        );
        const rewardToRemove = this.models["loyalty.reward"].filter((reward) =>
            programToRemoveIds.includes(reward.program_id.id)
        );
        this.models["loyalty.card"].deleteMany(cardsToRemove);
        this.models["loyalty.program"].deleteMany(programToRemove);
        this.models["loyalty.rule"].deleteMany(rulesToRemove);
        this.models["loyalty.reward"].deleteMany(rewardToRemove);
        if (this.config.self_ordering_mode != "mobile") {
            // Delete res partner from local data if we are not in mobile mode
            this.models["loyalty.card"]
                .filter((card) => card.partner_id)
                .forEach((card) => card.delete());
            this.models["res.partner"].deleteMany(this.models["res.partner"].getAll());
        }
    },
    async addToCart(
        productTemplate,
        qty,
        customer_note,
        selectedValues = {},
        customValues = {},
        comboValues = {}
    ) {
        await super.addToCart(...arguments);
        this.currentOrder.recomputeRewards();
        await this.checkAutomaticReward();
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
            partner = result["res.partner"].length > 0 && result["res.partner"][0];
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
            await this.currentOrder.recomputeRewards();
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
        await this.applyCode(code.code);
    },
    //#region Loyalty programs handling
    getLoyaltyCards() {
        const partner = this.currentOrder.getPartner();
        if (!partner) {
            return [];
        }
        const loyaltyCards = this.models["loyalty.card"].filter(
            (card) =>
                card.partner_id?.id === partner?.id && card.program_id.program_type === "loyalty"
        );
        return loyaltyCards;
    },
    getLoyaltyPrograms(rewardType = false, claimableOnly = false) {
        return this.getProgram(["loyalty"], rewardType, claimableOnly);
    },
    getPromotionPrograms(claimableOnly = false) {
        return this.getProgram(["promotion", "buy_x_get_y"], false, claimableOnly);
    },
    getProgram(programType = [], rewardType = false, claimableOnly = false) {
        const loyalty_programs = this.models["loyalty.program"].filter((program) =>
            programType.includes(program.program_type)
        );
        const loyaltyPrograms = {};
        for (const program of loyalty_programs) {
            loyaltyPrograms[program.id] = program.reward_ids;
            if (rewardType) {
                loyaltyPrograms[program.id] = loyaltyPrograms[program.id].filter(
                    (reward) => reward.reward_type === rewardType
                );
            }
            if (claimableOnly) {
                loyaltyPrograms[program.id] = loyaltyPrograms[program.id].filter(
                    (reward) => program.getPoints(this.currentOrder) >= reward.required_points
                );
            }
            if (loyaltyPrograms[program.id].length === 0) {
                delete loyaltyPrograms[program.id];
            }
        }
        return loyaltyPrograms;
    },
    //#region Reward application
    async checkAutomaticReward() {
        // Implement the logic to automatically apply rewards based on the current order
        const autoProductRewards = this.currentOrder.availableRewards.filter(
            (reward) =>
                reward.reward.program_id.trigger === "auto" &&
                reward.reward.reward_type === "product" &&
                reward.reward.program_id.applies_on === "current" &&
                !this.currentOrder.uiState.askedRewards.has(reward.reward.id)
        );
        await this.askRewards(autoProductRewards);
    },
    async askRewards(rewards) {
        let remaining = rewards.map((reward) => reward.reward);
        remaining.forEach((reward) => this.currentOrder.uiState.askedRewards.add(reward.id));
        while (remaining.length) {
            const reward = await makeAwaitable(this.dialog, SelectRewardPopup, {
                rewards: remaining,
                title: _t("You're eligible for those rewards, do you want them?"),
            });
            if (!reward) {
                break; // dialog closed without a choice
            }
            await this.applyReward(reward);
            remaining = remaining.filter((r) => r.id !== reward.id);
        }
    },
    async applyReward(reward) {
        if (!reward) {
            return;
        }
        if (reward.reward_type === "product") {
            await this.applyRewardProduct(reward);
        } else if (reward.reward_type === "discount") {
            this.applyRewardDiscount(reward);
        }
        this.currentOrder.recomputeRewards();
    },
    async applyRewardProduct(reward) {
        // Can be multiple products
        const order = this.currentOrder;
        const products = reward.reward_product_ids;
        const programId = reward.program_id.id;
        if (order.disabled_program_ids.includes(programId)) {
            order.disabled_program_ids = order.disabled_program_ids.filter(
                (id) => id !== programId
            );
            if (order.appliedPrograms.some((program) => program.id === programId)) {
                return;
            }
        }
        const applyProduct = async (reward_product_id) => {
            let attribute_value_ids = [];
            let attribute_custom_values = [];
            const productTmpl = reward_product_id.product_tmpl_id;
            if (productTmpl.isConfigurableForSelfOrder) {
                const attributeValues = await this.openConfigurator(productTmpl, {
                    presetVariant: reward_product_id,
                });
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
        };
        if (products.length === 1) {
            await applyProduct(products[0]);
            return;
        }
        const product = await makeAwaitable(this.dialog, SelectProductPopup, {
            products: new Set(products),
        });
        if (product) {
            await applyProduct(product);
        }
        return;
    },
    async openConfigurator(productTemplate, { presetVariant } = {}) {
        return makeAwaitable(this.dialog, SelectAttributePopup, {
            productTemplate,
            presetVariant,
        });
    },
    applyRewardDiscount(reward) {
        // Can be discount in %, $ or $ per point
        // Each can be on Order, cheapest product or specific product
        const order = this.currentOrder;
        order.active_rewards.push({ reward_id: reward.id });
    },
    async applyCode(code) {
        try {
            const data = await rpc(`/pos-self-order/check-card-code/`, {
                access_token: this.access_token,
                code: code,
                partner_id: this.currentOrder.getPartner()?.id || null,
                order_uuid: this.currentOrder.uuid,
            });
            if (!data["status"]) {
                const result = data["reason"];
                if (result === "invalid_partner") {
                    this.identifyCustomer(
                        _t(
                            "You tried to scan a code linked to a different customer. Please identify yourself if you want to use your code."
                        )
                    );
                } else if (result === "not_enough_points") {
                    this.notification.add(_t("Not enough points on your card to claim a reward."), {
                        type: "warning",
                    });
                } else if (result === "invalid_code") {
                    this.notification.add(_t("%s is an invalid coupon code.", code), {
                        type: "danger",
                    });
                }
                return data["status"];
            }
            this.models.connectNewData(data["data"]);
            const result = this.currentOrder.applyCode(code);
            if (!result.success) {
                this.notification.add(result.rejection_message, {
                    type: "warning",
                });
                return result.success;
            }
            this.currentOrder.recomputeRewards();
            return result.success;
        } catch {
            this.notification.add(
                _t("An error occurred while applying the code. Try again later."),
                {
                    type: "danger",
                }
            );
            return false;
        }
    },
    //#region Identify Customer
    async identifyCustomer(title = "") {
        // Open identification popup
        this.dialog.closeAll();
        const mail = await makeAwaitable(this.dialog, UserInputPopup, {
            text:
                title ||
                _t("Scan your customer barcode or fill in your mail address to identify yourself"),
            useMobileScanner: true,
            inputPlaceholder: _t("Enter your email address"),
            isValid: isValidEmail,
        });
        if (!mail) {
            return;
        }
        const existingMail = await this.identifyCustomerByMail(mail);
        if (existingMail) {
            const askValidationCode = async () => {
                const code = await makeAwaitable(this.dialog, UserInputPopup, {
                    text: _t(
                        "A verification code has been sent to %s. It's valid for 10 minutes. If you can't find it, check your spam folder.",
                        existingMail
                    ),
                    isValid: (input) => /^\d{6}$/.test(input),
                });
                return code;
            };
            let result = false;
            while (!result) {
                const code = await askValidationCode();
                if (!code) {
                    return;
                }
                result = await this.validateCustomerCode(code, existingMail);
            }
        }
    },
    async identifyCustomerByMail(mail) {
        const result = await rpc(`/pos-self-order/get-partner-by-mail/`, {
            access_token: this.access_token,
            mail: mail,
        });
        const data = result["data"];
        if (!result["new"]) {
            return mail;
        }
        this.addPartner(data);
        return false;
    },
    async validateCustomerCode(code, mail) {
        const result = await rpc(`/pos-self-order/validate-partner-code/`, {
            access_token: this.access_token,
            mail: mail,
            code: code,
        });
        if (result["res.partner"].length == 0) {
            return false;
        }
        this.addPartner(result);
        return true;
    },
    addPartner(data) {
        const records = this.models.connectNewData(data);
        const partner = records["res.partner"].length > 0 && records["res.partner"][0];
        if (!partner) {
            this.notification.add(_t("Customer not found"), {
                type: "danger",
            });
            return;
        }
        if (this.currentOrder.getPartner() !== partner) {
            this.currentOrder.setPartner(partner);
            this.currentOrder.recomputeRewards();
            this.notification.add(_t("Welcome back %s", partner.name), {
                type: "success",
            });
            this.dialog.closeAll();
        }
    },
});
