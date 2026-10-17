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
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";

patch(SelfOrder.prototype, {
    createNewOrder() {
        const order = super.createNewOrder();
        if (this.config.self_ordering_mode == "mobile") {
            this.deleteUnrelatedData();
            const partner = this.identifiedPartner;
            if (partner) {
                order.setPartner(partner);
            }
        }
        return order;
    },
    initData() {
        // Remove reward lines that have no reward anymore (could happen if the program got archived)
        this.models["pos.order.line"]
            .filter((line) => line.is_reward_line && !line.reward_id)
            .forEach((line) => line.delete());
        super.initData(...arguments);
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
        const result = await super.initMobileData(...arguments);
        if (this.config.self_ordering_mode === "mobile") {
            await this.refreshPartnerIdentification();
        }
        return result;
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
    /**
     * Forget the code-based programs and cards (and, outside mobile, the customers) that
     * the open orders don't use anymore: they can be found again by entering their code.
     * Called when a new customer may take over: on the kiosk landing page, and in mobile
     * when a new order starts or the customer logs out.
     */
    deleteUnrelatedData() {
        // What the open orders use must stay, or their rewards would disappear: in mobile
        // (pay after each order) an order sent to the counter stays open while a new one starts
        const openOrders = this.models["pos.order"].filter((order) => order.state === "draft");
        const usedCodes = new Set(openOrders.flatMap((order) => order.applied_codes || []));
        const usedCardIds = new Set(
            openOrders
                .flatMap((order) => [
                    ...order.lines.map((line) => line.card_id?.id),
                    ...(order.active_payment_programs || []).map((entry) => entry.card_id),
                ])
                .filter(Boolean)
        );
        const isUsedCard = (card) => usedCardIds.has(card.id) || usedCodes.has(card.code);
        const cardsToRemove = this.models["loyalty.card"].filter(
            (card) =>
                [
                    "coupons",
                    "promo_code",
                    "gift_card",
                    "promotion",
                    "buy_x_get_y",
                    "next_order_coupons",
                ].includes(card.program_id?.program_type) && !isUsedCard(card)
        );
        // Remove all programs and related stuff linked to codes
        const programToRemove = this.models["loyalty.program"].filter(
            (program) =>
                ["coupons", "promo_code", "next_order_coupons"].includes(program.program_type) &&
                !program.rule_ids.some((rule) => rule.code && usedCodes.has(rule.code)) &&
                !this.models["loyalty.card"].some(
                    (card) => card.program_id?.id === program.id && isUsedCard(card)
                )
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
            this.setIdentifiedPartner(false);
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
        if (!this.ordering || this.config.self_ordering_mode !== "kiosk") {
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
            partner = result["res.partner"]?.[0]; // the server sends no partner for an unknown barcode
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
        this.setIdentifiedPartner(partner);
        if (this.currentOrder.getPartner() !== partner) {
            this.currentOrder.setPartner(partner);
            await this.currentOrder.recomputeRewards();
            this.notification.add(_t("Welcome back %s", partner.name), {
                type: "success",
            });
            this.dialog.closeAll();
        }
    },
    /** Scan a code with the device's camera and handle it like a hardware scan. */
    async openMobileScanner() {
        // No reader when the company has no barcode nomenclature
        const barcodeReader = this.env.services.barcode_reader;
        if (!isBarcodeScannerSupported() || !barcodeReader) {
            this.notification.add(_t("Scanning isn't available on this device."), {
                type: "warning",
            });
            return;
        }
        let data;
        try {
            data = await scanBarcode(this.env);
        } catch (error) {
            // Here, we know the structure of the error raised by BarcodeScanner.
            this.dialog.add(AlertDialog, {
                title: _t("Unable to scan"),
                body:
                    error?.message ||
                    error?.error?.message ||
                    _t("Unable to find barcode scanner."),
            });
            return;
        }
        if (data) {
            barcodeReader.scan(data);
            if ("vibrate" in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.notification.add(_t("Please, Scan again!"), {
                type: "warning",
            });
        }
    },
    async _barcodeCouponCodeAction(code) {
        if (!this.ordering) {
            return;
        }
        this.dialog.closeAll();
        const applied = await this.applyCode(code.code);
        if (applied && this.router.activeSlot === "payment") {
            await this.syncCodeAppliedOnPaymentPage();
        }
        return applied;
    },
    /**
     * The order was sent when the payment page opened: a code applied there (gift card,
     * eWallet...) only exists locally, while the confirmation page or a new payment attempt
     * reload the order from the server.
     */
    async syncCodeAppliedOnPaymentPage() {
        const order = await this.sendDraftOrderToServer();
        if (order && this.currency.isZero(order.priceIncl)) {
            this.confirmationPage("pay", this.config.self_ordering_mode, order.access_token);
        }
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
                !this.currentOrder.uiState.askedRewards.includes(reward.reward.id)
        );
        await this.askRewards(autoProductRewards);
    },
    async askRewards(rewards) {
        let remaining = rewards.map((reward) => reward.reward);
        const askedRewards = this.currentOrder.uiState.askedRewards;
        askedRewards.push(...remaining.map((reward) => reward.id).filter((id) => !askedRewards.includes(id)));
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
            let attribute_custom_values = {};
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
                reward_product_id: reward_product_id.id,
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
        title ||=
            this.config.self_ordering_mode === "kiosk"
                ? _t(
                      "Scan your customer barcode or fill in your mail address to identify yourself."
                  )
                : _t("Fill in your mail address to identify yourself.");
        const mail = await makeAwaitable(this.dialog, UserInputPopup, {
            text: title,
            inputPlaceholder: _t("Enter your email address"),
            isValid: isValidEmail,
        });
        if (!mail) {
            return;
        }
        let request;
        try {
            request = await rpc(`/pos-self-order/get-partner-by-mail/`, {
                access_token: this.access_token,
                mail: mail,
            });
        } catch (error) {
            this.handleErrorNotification(error);
            return;
        }
        if (request["too_many_attempts"]) {
            this.notifyTooManyAttempts();
            return;
        }
        // A code is sent to new and known emails alike: the customer is only identified
        // (or created) once it proves it owns the mailbox
        let identified = false;
        while (!identified) {
            const code = await makeAwaitable(this.dialog, UserInputPopup, {
                text: _t(
                    "A verification code has been sent to %s. It's valid for 10 minutes. If you can't find it, check your spam folder.",
                    mail
                ),
                isValid: (input) => /^\d{6}$/.test(input),
            });
            if (!code) {
                return;
            }
            const result = await this.validateCustomerCode(code, mail);
            identified = result.identified;
            if (result.tooManyAttempts) {
                this.notifyTooManyAttempts();
                return;
            }
            if (!identified) {
                this.notification.add(_t("This code is wrong or has expired."), { type: "danger" });
            }
        }
    },
    async validateCustomerCode(code, mail) {
        const result = await rpc(`/pos-self-order/validate-partner-code/`, {
            access_token: this.access_token,
            mail: mail,
            code: code,
        });
        if (result["res.partner"].length == 0) {
            return { identified: false, tooManyAttempts: Boolean(result["too_many_attempts"]) };
        }
        this.addPartner(result);
        return { identified: true, tooManyAttempts: false };
    },
    notifyTooManyAttempts() {
        this.notification.add(_t("Too many attempts, please try again later."), {
            type: "danger",
        });
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
        this.setIdentifiedPartner(partner);
        if (this.currentOrder.getPartner() !== partner) {
            this.currentOrder.setPartner(partner);
            this.currentOrder.recomputeRewards();
            this.notification.add(_t("Welcome back %s", partner.name), {
                type: "success",
            });
            this.dialog.closeAll();
        }
    },
    //#region Identification token
    get identifiedPartnerStorageKey() {
        return `pos_self_order_loyalty.identified_partner_id.${this.config.id}`;
    },
    /**
     * The partner the customer identified as (barcode, email code...), as opposed to other
     * partners the device may hold (e.g. one created by the delivery address form).
     * Remembered across reloads in mobile only: a kiosk is a shared device.
     */
    get identifiedPartner() {
        if (this._identifiedPartnerId === undefined) {
            this._identifiedPartnerId = null;
            if (this.config.self_ordering_mode === "mobile") {
                try {
                    // the signed partner id ("<id>-<hmac>"), see pos.order._get_signed_self_partner_id
                    this._identifiedPartnerId =
                        localStorage.getItem(this.identifiedPartnerStorageKey) || null;
                } catch {
                    // storage unavailable (private browsing...): identification isn't remembered
                }
            }
        }
        return this._identifiedPartnerId
            ? this.models["res.partner"].get(this._identifiedPartnerId)
            : undefined;
    },
    setIdentifiedPartner(partner) {
        this._identifiedPartnerId = partner?.id || null;
        if (this.config.self_ordering_mode !== "mobile") {
            return;
        }
        try {
            if (this._identifiedPartnerId) {
                localStorage.setItem(
                    this.identifiedPartnerStorageKey,
                    String(this._identifiedPartnerId)
                );
            } else {
                localStorage.removeItem(this.identifiedPartnerStorageKey);
            }
        } catch {
            // storage unavailable (private browsing...): identification isn't remembered
        }
    },
    /** Refresh the identified partner's data (points...), or ask to log in again if the server
     * doesn't recognize it anymore. */
    async refreshPartnerIdentification() {
        const partner = this.identifiedPartner;
        if (!partner) {
            return;
        }
        let data;
        try {
            data = await rpc(`/pos-self-order/get-identified-partner`, {
                access_token: this.access_token,
                partner_id: partner.id,
            });
        } catch {
            return; // offline or server error: keep the identification, the next order will tell
        }
        if (data["res.partner"].length === 0) {
            this.expireIdentification(partner);
            return;
        }
        this.models.connectNewData(data);
        this.data.debouncedSynchronizeLocalDataInIndexedDB();
    },
    /** Forget the identified partner on this device, e.g. on log out. */
    logoutPartner() {
        const partner = this.identifiedPartner || this.currentOrder.getPartner();
        this.setIdentifiedPartner(false);
        if (this.config.self_ordering_mode === "mobile") {
            this.deleteUnrelatedData();
        }
        if (!partner) {
            return;
        }
        if (this.currentOrder.getPartner() === partner) {
            this.currentOrder.setPartner(false); // also drops the partner and its cards locally
            this.currentOrder.recomputeRewards();
        } else {
            this.models["loyalty.card"]
                .filter((card) => card.partner_id?.id === partner.id)
                .forEach((card) => card.delete());
            partner.delete();
        }
        this.data.debouncedSynchronizeLocalDataInIndexedDB();
    },
    expireIdentification(partner = this.currentOrder.getPartner()) {
        if (partner && partner !== this.identifiedPartner) {
            // The rejected partner isn't the identified one (e.g. created by the address form)
            this.currentOrder.setPartner(false);
            this.currentOrder.recomputeRewards();
        } else {
            this.logoutPartner();
        }
        this.identifyCustomer(
            _t("Your identification has expired, please identify yourself again.")
        );
    },
});
