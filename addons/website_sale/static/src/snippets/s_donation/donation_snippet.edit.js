import { DonationSnippet } from "./donation_snippet";
import { registry } from "@web/core/registry";

const DonationSnippetEdit = (I) =>
    class extends I {
        // TODO: Handle the `s_donation_description_inputs` positioning in XML
        // in master instead of the interaction. It is currently handled in JS
        // to support snippets that were already dropped.
        setup() {
            super.setup();
            const descriptionInputsEl = this.el.querySelector(
                ":scope:not(.s_donation_inline) #s_donation_description_inputs"
            );
            const parentEl = descriptionInputsEl?.parentElement;
            if (parentEl && parentEl.firstElementChild !== descriptionInputsEl) {
                parentEl.prepend(descriptionInputsEl);
            }
        }

        onDonateClick() {}
};

registry
    .category("public.interactions.edit")
    .add("website_sale.donation_snippet", {
        Interaction: DonationSnippet,
        mixin: DonationSnippetEdit,
    });
