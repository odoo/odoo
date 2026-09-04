import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";
import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { InvalidDomainError } from "@web/core/domain";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.updateRewards();
        this.loadPartnerCardsAsync(
            this.models["pos.order"]
                .filter((order) => !order.finalized)
                .map((order) => order.partner_id?.id)
        );
    },
    async afterProcessServerData() {
        // Remove reward lines that have no reward anymore (could happen if the program got archived)
        this.models["pos.order.line"]
            .filter((order) => order.is_reward_line && !order.reward_id)
            .map((line) => line.delete());
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
                    showReloadButton: true,
                });
                reward.delete();
            }
        }
    },
    async addLineToCurrentOrder(vals, opt = {}, configure = true) {
        // A gift card / eWallet trigger product funds a loyalty program. Resolve which
        // program and remember it on the line via `gift_card_vals`
        const program = opt.paymentProgram ?? (await this._getTriggeredPaymentProgram(vals));
        if (program === false) {
            return;
        }
        const orderTotal = this.getOrder()?.priceIncl ?? 0;
        if (program && orderTotal < 0) {
            vals.price_unit = -orderTotal;
        }
        if (program) {
            // When selling a gift card or an eWallet product, we should not put taxes on it.
            // When buying a gift card and spending it on products, the taxes are applied
            // on the products, not on the gift card. A gift card line should thus never have taxes.
            vals.tax_ids = [];
        }
        const line = await super.addLineToCurrentOrder(vals, opt, configure);
        if (line && program) {
            line.gift_card_vals = { ...line.gift_card_vals, program_id: program.id };
        }
        this.updateRewards();
        return line;
    },
    async selectPreset(preset = false, order = this.getOrder(), presetSelection = false) {
        const res = await super.selectPreset(...arguments);
        if (order.serviceFeeLines.length > 0) {
            // A preset can change the pricelist / fiscal position / service fee, which
            // impacts reward amounts (a gift card covers the total, fee included). The
            // fee goes first and synchronously (its own recompute is debounced).
            this.getOrder()?.recomputeServiceFees();
            await this.updateRewards();
        }
        return res;
    },
    setPartnerToCurrentOrder(partner) {
        super.setPartnerToCurrentOrder(partner);
        this.loadPartnerCardsAsync([partner?.id]);
        this.getOrder()?.removeNominativeRewards();
        this.updateRewards();
    },
    /**
     * Load the given partners' loyalty cards without blocking the caller, then recompute
     * the rewards so the freshly loaded balances become spendable.
     *
     * @param {(number|undefined)[]} partnerIds - falsy entries are ignored
     */
    loadPartnerCardsAsync(partnerIds) {
        partnerIds = partnerIds.filter(Boolean);
        if (!partnerIds.length) {
            return;
        }
        this.loadPartnerCards(partnerIds)
            .then(() => this.updateRewards())
            .catch((error) =>
                logPosMessage(
                    "PosStore",
                    "loadPartnerCardsAsync",
                    "Could not load the customer's loyalty cards",
                    false,
                    [error]
                )
            );
    },
    /**
     * Load into memory the loyalty cards of the given partners for this config's
     * programs. `search_read` auto-connects the records into `models["loyalty.card"]`,
     * so their balances become available to the reward computation and the points
     * display. Loyalty cards aren't loaded at startup, so the partner list calls this
     * for every partner it fetches.
     * @param {number[]} partnerIds
     */
    async loadPartnerCards(partnerIds) {
        partnerIds = [...new Set(partnerIds.filter(Boolean))];
        const programIds = this.models["loyalty.program"].map((program) => program.id);
        if (!partnerIds.length || !programIds.length) {
            return;
        }
        await this.data.searchRead(
            "loyalty.card",
            [
                ["partner_id", "in", partnerIds],
                ["program_id", "in", programIds],
            ],
            this.data.fields["loyalty.card"]
        );
    },
    /**
     * Resolve the gift_card/eWallet program a trigger product belongs to.
     * @param {object} vals - the values passed to addLineToCurrentOrder
     * @returns {Promise<object|null|false>} the program, null when the product triggers
     *   none, or false when the cashier cancelled the selection popup.
     */
    async _getTriggeredPaymentProgram(vals) {
        const productTmpl = vals.product_tmpl_id || vals.product_id?.product_tmpl_id;
        if (!productTmpl) {
            return null;
        }
        const programs = [
            ...new Set(
                productTmpl.product_variant_ids
                    .flatMap(
                        (variant) =>
                            this.models["loyalty.program"].getBy(
                                "trigger_product_ids",
                                variant.id
                            ) || []
                    )
                    .filter((p) => ["gift_card", "ewallet"].includes(p.program_type))
            ),
        ];
        if (programs.length === 0) {
            return null;
        }
        let program;
        if (programs.length === 1) {
            program = programs[0];
        } else {
            program = await makeAwaitable(this.dialog, SelectionPopup, {
                title: _t("Select program"),
                list: programs.map((program) => ({
                    id: program.id,
                    item: program,
                    label: program.name,
                })),
            });
        }
        if (!program) {
            return false;
        }
        if (program.is_nominative && !this.getOrder()?.partner_id) {
            await this.selectPartner();
            if (!this.getOrder()?.partner_id) {
                return false;
            }
        }
        return program;
    },
    /**
     * Recomputes the automatically applied rewards on the current order.
     * Called from every action that mutates the order (add/remove line, quantity change, ...).
     */
    updateRewards() {
        this.getOrder()?.recomputeRewards();
        // Update the customer display after loyalty changes, as they are stored in the UI state
        // and do not trigger the order record's `create` event.
        this.debounceUpdateCustomerDisplay();
    },
    /**
     * Recompute the rewards when the pricelist changes
     */
    async selectPricelist(pricelist) {
        await super.selectPricelist(pricelist);
        this.updateRewards();
    },
    /**
     * Ensure the loyalty card for a scanned/typed code is loaded into memory.
     * If it's not in memory, load from the backend (loyalty.card.get_card_status)
     * and connect into the local models
     * @param {string} code
     * @returns {Promise<string>} "" when the card is in memory, otherwise the rejection reason
     */
    async loadCode(code) {
        let card = this.models["loyalty.card"].find((card) => card.code === code);

        let result = null;
        if (!card) {
            const isDiscountCode = this.models["loyalty.rule"].some((rule) => rule.matchCode(code));
            if (isDiscountCode) {
                return "";
            }
            result = await this.data.call("loyalty.card", "get_card_status", [
                code,
                this.config.id,
            ]);
            if (!result["loyalty.card"].length) {
                return _t("That coupon is invalid (%s).", code);
            }

            const partnerId = result["loyalty.card"][0].partner_id;
            if (partnerId && !this.models["res.partner"].get(partnerId)) {
                await this.data.read("res.partner", [partnerId]);
            }

            const payload = { "loyalty.card": result["loyalty.card"] };
            this.data.synchronizeServerDataInIndexedDB(payload);
            this.models.loadConnectedData(payload);
            card = this.models["loyalty.card"].get(result["loyalty.card"][0].id);
        }

        if (card?.isExpired()) {
            return _t("That card has expired (%s).", code);
        }

        if (result && card?.program_id?.program_type === "gift_card" && !result.has_source_order) {
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
        return "";
    },
    async applyCode(code) {
        const order = this.getOrder();
        const result = order.applyCode(code);
        if (!result.success) {
            this.notification.add(result.rejection_message, { type: "danger" });
            return;
        }
        const program = result.program_id;
        if (program.reward_ids.length > 1 && !program.is_payment_program) {
            const reward = await makeAwaitable(this.dialog, SelectionPopup, {
                title: _t("Please select a reward"),
                list: program.reward_ids.map((reward) => ({
                    id: reward.id,
                    item: reward,
                    label: reward.description,
                })),
            });
            const rewardEntry = { reward_id: reward.id };
            if (reward.multi_product) {
                const reward_product_id = await makeAwaitable(this.dialog, SelectionPopup, {
                    title: _t("Please select a product for this reward"),
                    list: reward.reward_product_ids.map((product) => ({
                        id: product.id,
                        item: product,
                        label: product.display_name,
                    })),
                });
                if (!reward_product_id) {
                    return "";
                }
                rewardEntry.reward_product_id = reward_product_id;
            }
            order.active_rewards.push(rewardEntry);
        }
    },
});
