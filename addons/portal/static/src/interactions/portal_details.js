import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PortalDetails extends Interaction {
    static selector = ".o_portal_details";
    dynamicContent = {
        "select[name=country_id]": {
            "t-on-change": this.adaptAddressForm,
        },
    };

    setup() {
        this.stateEl = this.el.querySelector("select[name=state_id]");
        this.stateOptionEls = this.el.querySelectorAll(
            "select[name=state_id]:not([disabled]):not([disabled=false]) option:not(:first-child)"
        );
        this.adaptAddressForm();
    }

    adaptAddressForm() {
        const countryEl = this.el.querySelector("select[name=country_id]");
        const countryID = countryEl.value || 0;
        for (const optionEl of this.stateOptionEls) {
            optionEl.remove();
        }
        let nb = 0;
        for (const el of this.stateOptionEls) {
            if (el.dataset.country_id === countryID) {
                el.classList.remove("d-none");
                this.stateEl.appendChild(el);
                nb++;
            }
        }
        this.stateEl.classList.remove("d-none");
        this.stateEl.parentElement.classList[nb >= 1 ? "remove" : "add"]("d-none");
    }
}

registry.category("public.interactions").add("portal.portal_details", PortalDetails);
