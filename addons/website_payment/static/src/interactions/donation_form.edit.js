import { DonationForm } from "./donation_form";
import { registry } from "@web/core/registry";

export const DonationPaymentFormEdit = (I) =>
    class extends I {
        start() {
            this.selectEl = document.querySelector("#country_id");
            const selectedOption = this.selectEl.querySelector("option[selected]");
            if (selectedOption) {
                selectedOption.selected = false;
            }
        }
    };

registry.category("public.interactions.edit").add("website_payment.donation_form", {
    Interaction: DonationForm,
    mixin: DonationPaymentFormEdit,
});
