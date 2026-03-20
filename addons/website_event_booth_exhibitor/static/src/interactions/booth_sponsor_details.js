import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class BoothSponsorDetails extends Interaction {
    static selector = "#o_wbooth_contact_details_form";
    dynamicContent = {
        "input[id='contact_details']": { "t-on-click.withTarget": this.onClickContactDetails },
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} currentTargetEl
     */
    onClickContactDetails(ev, currentTargetEl) {
        this.useContactDetails = currentTargetEl.checked;

        const contactDetailsEl = this.el.querySelector("#o_wbooth_contact_details");
        contactDetailsEl.classList.toggle("d-none", !this.useContactDetails);

        const sponsorInfoEls = this.el.querySelectorAll("label[for='sponsor_name'] > .mandatory_mark, label[for='sponsor_email'] > .mandatory_mark");
        for (const sponsorInfoEl of sponsorInfoEls) {
            sponsorInfoEl.classList.toggle("d-none", this.useContactDetails);
        }

        const contactInfoEls = this.el.querySelectorAll("input[name='contact_name'], input[name='contact_email']");
        for (const contactInfoEl of contactInfoEls) {
            contactInfoEl.required = this.useContactDetails;
        }
    }
}

registry
    .category("public.interactions")
    .add("website_event_booth_exhibitor.booth_sponsor_details", BoothSponsorDetails);
