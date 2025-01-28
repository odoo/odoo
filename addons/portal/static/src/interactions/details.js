import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class Details extends Interaction {
    static selector = ".o_portal_details";
    dynamicContent = {
        "select[name='country_id']": { "t-on-change": this.onCountryChange },
    };

    setup() {
        this.stateSelectEl = this.el.querySelector("select[name='state_id']");
        this.stateOptionEls = [];
        if (!this.stateSelectEl.getProperty("disabled")) {
            this.stateOptionEls = this.stateSelectEl.querySelectorAll("option:not(:first)");
        }
    }

    start() {
        this.onCountryChange();
    }

    onCountryChange() {
        const countryEl = this.el.querySelector("select[name='country_id']");
        const countryId = countryEl.value || 0;
        let displayedStateEl = undefined;
        for (const stateOptionEl of this.stateOptionEls) {
            if (stateOptionEl.dataset.country_id == countryId) {
                displayedStateEl = stateOptionEl.cloneNone();
            }
            stateOptionEl.remove();
        }
        this.insert(displayedStateEl, this.stateSelectEl);
        displayedStateEl.removeClass("d-none");
        displayedStateEl.style.display = "";
        this.stateSelectEl.parentElement.style.display = displayedStateEl ? "" : "none";
    }
}

registry
    .category("public.interactions")
    .add("portal.details", Details);
