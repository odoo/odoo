import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class DonationForm extends Interaction {
    static selector = ".o_donation_payment_form";
    dynamicContent = {
        ".o_amount_input": { "t-on-focus": this.onFocusAmountInput },
        "#donation_comment_checkbox": { "t-on-change.withTarget": this.onDonationCommentChange },
        "input[type='radio']": { "t-on-change": this.onSelectRadioButton },
        "#other_amount_value": { "t-on-input": this.onChangeAmountInput },
    };

    /**
     * @param {Event} ev
     */
    onFocusAmountInput(ev) {
        const otherAmountEl = this.el.querySelector("#other_amount");
        if (otherAmountEl) {
            otherAmountEl.checked = true;
        }
    }
    /**
     * @param {Event} ev
     * @param {HTMLElement} currentTargetEl
     */
    onDonationCommentChange(ev, currentTargetEl) {
        const checked = currentTargetEl.checked;
        const donationCommentEl = this.el.querySelector('#donation_comment');
        donationCommentEl.classList.toggle('d-none', !checked);
        if (!checked) {
            donationCommentEl.value = "";
        }
    }
    /**
     * Validates the custom donation amount input field.
     * Displays a warning if the input is empty, zero, or invalid.
     * Shows warnings if the amount is below the minimum or above the
     * maximum allowed.
     *
     */
    onChangeAmountInput() {
        const inputEl = this.el.querySelector("#other_amount_value");
        const warningMessageEl = this.el.querySelector("#warningMessageId");
        const warningMinMessageEl = this.el.querySelector("#warningMinMessageId");
        const value = parseFloat(inputEl.value);
        warningMessageEl.classList.toggle("d-none", value);
        warningMinMessageEl?.classList.toggle("d-none", value ? inputEl.min < value : true);
    }
    /**
     * Handles selection of donation amount options.
     * If "Other Amount" is selected, triggers validation for custom input
     * else clears the custom amount input and hides all warnings when other
     * options are chosen.
     *
     * @param {Event} ev
     */
    onSelectRadioButton(ev) {
        if (ev.currentTarget.id === "other_amount") {
            return this.el.querySelector("#other_amount_value").focus();
        }
        this.el.querySelector("#other_amount_value").value = "";
        this.el.querySelector("#warningMinMessageId").classList.add("d-none");
        this.el.querySelector("#warningMessageId").classList.add("d-none");
    }
}

registry
    .category("public.interactions")
    .add("website_payment.donation_form", DonationForm);
