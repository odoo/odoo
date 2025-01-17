import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class DonationForm extends Interaction {
    static selector = ".o_donation_payment_form";
    dynamicContent = {
        ".o_amount_input": { "t-on-focus": () => this.el.querySelector("#other_amount")?.setAttribute("checked", true) },
        "#donation_comment_checkbox": { "t-on-change.withTarget": this.onDonationCommentChange },
    };

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
}

registry
    .category("public.interactions")
    .add("website_payment.donation_form", DonationForm);
