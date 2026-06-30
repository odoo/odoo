import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class InvoiceSendingMethod extends Interaction {
    static selector = ".o_portal_details select[name='invoice_sending_method']";
    dynamicContent = {
        _root: { "t-on-change": this.showPeppolConfig },
    };

    start() {
        this.showPeppolConfig();
    }

    showPeppolConfig() {
        const method = this.el.value;
        const peppolToggleEls = document.querySelectorAll(".portal_peppol_toggle");
        for (const peppolToggleEl of peppolToggleEls) {
            peppolToggleEl.classList.toggle("d-none", method !== "peppol");
        }
    }
}

registry
    .category("public.interactions")
    .add("account_peppol.invoice_sending_method", InvoiceSendingMethod);
