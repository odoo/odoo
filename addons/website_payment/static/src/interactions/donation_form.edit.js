import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class DonationPaymentFormEdit extends Interaction {
    static selector = ".o_payment_field_form";
    start() {
        this.selectEl = this.el.querySelector("select");

        this.isDisabled = this.selectEl?.hasAttribute("disabled");
        if (this.isDisabled) {
            this.selectEl.removeAttribute("disabled");
        }

        const selectedOption = this.selectEl.querySelector("option[selected]");
        if (selectedOption) {
            selectedOption.selected = false;
        }
    }
}

registry
    .category("public.interactions.edit")
    .add("donation.form", {
        Interaction: DonationPaymentFormEdit,
    });
