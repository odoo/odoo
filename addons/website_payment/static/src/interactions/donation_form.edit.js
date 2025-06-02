import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class DonationPaymentFormEdit extends Interaction {
    static selector = ".o_payment_field_form";
    start() {
        this.readOnlyEls = this.el.querySelectorAll("input[readonly], textarea[readonly]");
        this.selectEl = this.el.querySelector("select");

        this.readOnlyEls.forEach((el) => {
            el.removeAttribute("readonly");
        });

        // this.isDisabled = this.selectEl?.hasAttribute("disabled");
        // if (this.isDisabled) {
        //     this.selectEl.removeAttribute("disabled");
        // }

        // const selectedOption = this.selectEl.querySelector("option[selected]");
        // this.defaultCountryValue = selectedOption?.value;
        // if (selectedOption) {
        //     selectedOption.selected = false;
        // }
    }

    destroy() {
        this.readOnlyEls.forEach((el) => {
            el.setAttribute("readonly", "1");
        });
        // ToDo: this is not workiong as expected, need to check why
        // if (this.defaultCountryValue) {
        //     const anotherEl = this.el.querySelector("select option[selected]");
        //     if (anotherEl) {
        //         anotherEl.selected = false;
        //     }
        //     this.selectEl.querySelector("option[value='" + this.defaultCountryValue + "']").selected = true;
        // }

        // if (this.isDisabled) {
        //     this.selectEl.setAttribute("disabled", "1");
        // }
    }
}

registry
    .category("public.interactions.edit")
    .add("donation.form", {
        Interaction: DonationPaymentFormEdit,
    });
