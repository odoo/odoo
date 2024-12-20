import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class WebsitePaymentDonation extends Interaction {
    static selector = ".o_donation_payment_form";
    dynamicContent = {
        ".o_amount_input": { "t-on-focus": this.onFocusAmountInput },
        "#donation_comment_checkbox": { "t-on-change": this.onChangeDonationComment },
    };

    /**
     * @param {Event} ev
     */
    onFocusAmountInput(ev) {
        const otherAmount = this.el.querySelector("#other_amount");
        if (otherAmount) {
            otherAmount.checked = true;
        }
    }

    /**
     * @param {Event} ev
     */
    onChangeDonationComment(ev) {
        const checked = ev.currentTarget.checked;
        const donationCommentEl = this.el.querySelector('#donation_comment');
        donationCommentEl.classList.toggle('d-none', !checked);
        if (!checked) {
            donationCommentEl.value = "";
        }
    }
}

registry
    .category("public.interactions")
    .add("website_payment.website_payment_donation", WebsitePaymentDonation);
