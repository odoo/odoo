import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

const CUSTOM_BUTTON_EXTRA_WIDTH = 10;

export class DonationSnippet extends Interaction {
    static selector = ".s_donation";
    dynamicContent = {
        ".s_donation_btn": {
            "t-on-click.withTarget": this.onPrefilledClick,
            "t-att-class": (el) => ({ "active": el === this.activeButtonEl }),
        },
        ".s_donation_donate_btn": {
            "t-on-click": this.locked(this.submitDonation, true),
            "t-att-class": () => ({ "o_ready_to_donate": true }), // See TEST_01_DONATION_FIX
        },
        "#s_donation_range_slider": { "t-on-input": this.onRangeSliderInput },
        "#s_donation_amount_input": {
            "t-on-input": () => {
                this.el.querySelector(".o_donation_custom_btn_warning")?.classList.add("d-none");
            },
        },
    };

    setup() {
        this.currency = null;
        this.donationInfo = null;
        this.activeButtonEl = null;
        this.rangeSliderEl = this.el.querySelector("#s_donation_range_slider");
        this.defaultAmount = this.el.dataset.defaultAmount;
        if (!!this.rangeSliderEl) {
            this.rangeSliderEl.value = this.defaultAmount;
            this.setBubble();
        }
    }

    async willStart() {
        // TODO this is not perfect compared to 18.0: there can be a delay where
        // the donation button does nothing because the currency is being
        // loaded (while before it waited for the currency inside the handler).
        // See TEST_01_DONATION_FIX which was adapted to this new behavior, as
        // it cannot be restored at the moment: if willStart don't await this,
        // there needs to be an asynchronous update of the DOM in start... which
        // edit mode warns about, as start is not awaited anywhere.
        // TODO the "cached" parameters has no effect: the actual cache is not
        // initialized on the frontend side at the moment.
        // TODO Also it should be the third param of rpc, not the second one...
        [this.currency, this.donationInfo] = await Promise.all([
            rpc("/website/get_current_currency", { cache: true }),
            rpc("/shop/donation/info"),
        ]);
    }

    start() {
        const prefilledButtonEls = this.el.querySelectorAll(".s_donation_btn, .s_range_bubble");
        for (const prefilledButtonEl of prefilledButtonEls) {
            // Remove existing currency
            prefilledButtonEl.querySelector(".s_donation_currency")?.remove();
            const insertBefore = this.currency.position === "before";
            const currencyEl = document.createElement("span");
            currencyEl.innerText = this.currency.symbol;
            currencyEl.classList.add("s_donation_currency", insertBefore ? "pe-1" : "ps-1");
            this.insert(currencyEl, prefilledButtonEl, insertBefore ? "afterbegin" : "beforeend");
        }

        const customButtonEl = this.el.querySelector("#s_donation_amount_input");
        if (customButtonEl) {
            this.registerCleanup(() => { customButtonEl.style.maxWidth = "" });
            const canvasEl = document.createElement("canvas");
            const context = canvasEl.getContext("2d");
            context.font = window.getComputedStyle(customButtonEl).font;
            const width = context.measureText(customButtonEl.placeholder).width;
            customButtonEl.style.maxWidth = `${Math.ceil(width) + CUSTOM_BUTTON_EXTRA_WIDTH}px`;
        }
    }

    setBubble() {
        const bubbleEl = this.el.querySelector(".s_range_bubble");
        const val = this.rangeSliderEl.value;
        const min = this.rangeSliderEl.min || 0;
        const max = this.rangeSliderEl.max || 100;
        const newVal = Number(((val - min) * 100) / (max - min));
        const tipOffsetLow = 8 - (newVal * 0.16); // the range thumb size is 16px*16px. The '8' and the '0.16' are related to that 16px (50% and 1% of 16px)

        for (const child of bubbleEl.childNodes) {
            if (child.nodeType === 3) {
                child.nodeValue = val;
            }
        }
        // Sorta magic numbers based on size of the native UI thumb (source: https://css-tricks.com/value-bubbles-for-range-inputs/)
        bubbleEl.style.insetInlineStart = `calc(${newVal}% + (${tipOffsetLow}px))`;
    }

    /**
     * @param {Event} ev
     * @param {HTMLElement} currentTargetEl
     */
    onPrefilledClick(ev, currentTargetEl) {
        this.activeButtonEl = currentTargetEl;
        const amountInputEl = this.el.querySelector("#s_donation_amount_input");
        if (!currentTargetEl.classList.contains("s_donation_custom_btn") && amountInputEl) {
            this.el.querySelector(".o_donation_custom_btn_warning")?.classList.add("d-none");
            amountInputEl.value = "";
        }
        if (this.rangeSliderEl) {
            this.rangeSliderEl.value = this.activeButtonEl.dataset.donationValue;
            this.setBubble();
        }
    }

    async submitDonation() {
        this.el.querySelector(".alert-danger")?.remove();  // Clean the error message, if any
        const amount = this._getDonationAmount();
        if (amount === null) {
            return;
        }
        if (!Object.keys(this.donationInfo || {}).length) {
            this._showDonationError(_t("Donation product not found."));
            return;
        }
        await this._addDonationToCart(amount);
    }

    /**
     * Get the donation amount from the active button, range slider, custom input, or default.
     * Returns null if validation fails (error is shown to the user).
     *
     * @returns {number|null}
     */
    _getDonationAmount() {
        let amount;
        if (this.activeButtonEl?.dataset.donationValue) {  // Pre-filled button selected by the user
            amount = parseFloat(this.activeButtonEl.dataset.donationValue);
        } else if (this.el.dataset.displayOptions) {
            if (this.rangeSliderEl) {  // Range slider
                amount = parseFloat(this.rangeSliderEl.value);
            // Custom amount input
            } else if (this.el.querySelectorAll(".s_donation_btn").length) {
                amount = parseFloat(this.el.querySelector("#s_donation_amount_input")?.value);
                const errorMessage = this._getAmountValidationError(amount);
                if (errorMessage) {
                    this._showDonationError(errorMessage, "o_donation_custom_btn_warning");
                    return null;
                }
            }
        }
        // Fall back to the snippet's configured default amount
        return amount || parseFloat(this.defaultAmount);
    }

    /**
     * @param {number} amount
     * @returns {string} error message, or empty string if valid
     */
    _getAmountValidationError(amount) {
        const minAmount = parseFloat(this.el.dataset.minimumAmount || "1");
        if (!amount) {
            return _t("Please select or enter an amount");
        }
        if (amount < minAmount) {
            return _t("The minimum donation amount is %(amount)s", {
                amount: formatCurrency(minAmount, this.currency.id),
            });
        }
        return "";
    }

    /**
     * @param {string} message
     * @param {...string} extraClasses
     */
    _showDonationError(message, ...extraClasses) {
        const pEl = document.createElement("p");
        pEl.classList.add("alert", "alert-danger", ...extraClasses);
        pEl.innerText = message;
        this.insert(pEl, this.el.querySelector(".s_donation_donate_btn"), "beforebegin");
    }

    /**
     * @param {number} amount
     */
    async _addDonationToCart(amount) {
        const isOnCartPage = !!document.getElementById("shop_cart");
        await this.services.cart.add(
            this._getDonationCartParams(amount),
            {
                isConfigured: true,
                isBuyNow: isOnCartPage, // Force reload of the cart page
            },
        );
    }

    /**
     * Return the parameters to pass to the cart service when adding a donation.
     *
     * @param {number} amount - The donation amount.
     * @returns {Object} The parameters to pass to the cart service.
     */
    _getDonationCartParams(amount) {
        return {
            productTemplateId: this.donationInfo.product_template_id,
            productId: this.donationInfo.product_id,
            quantity: 1,
            donation_amount: amount,
        };
    }

    onRangeSliderInput() {
        this.activeButtonEl = null;
        this.setBubble();
    }
}

registry.category("public.interactions").add("website_sale.donation_snippet", DonationSnippet);
