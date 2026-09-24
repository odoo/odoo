import { DonationSnippet } from "./donation_snippet";
import { registry } from "@web/core/registry";

const DonationSnippetEdit = (I) =>
    class extends I {
        // TODO: Handle `s_donation_description_inputs` positioning in XML in
        // master so translation inputs appear in the same position as the
        // descriptions in normal mode. Handle this in JS for now to also
        // support snippets that were already dropped.
        setup() {
            super.setup();
            const descriptionInputsEl = this.el.querySelector(
                ":scope:not(.s_donation_inline) #s_donation_description_inputs:not(:first-child)"
            );
            descriptionInputsEl?.parentElement.prepend(descriptionInputsEl);
        }

        submitDonation() {}
};

registry
    .category("public.interactions.edit")
    .add("website_sale.donation_snippet", {
        Interaction: DonationSnippet,
        mixin: DonationSnippetEdit,
    });
