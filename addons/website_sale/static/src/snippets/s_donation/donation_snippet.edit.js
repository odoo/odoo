import { DonationSnippet } from "./donation_snippet";
import { registry } from "@web/core/registry";

const DonationSnippetEdit = (I) =>
    class extends I {
        // TODO: Remove the `s_donation_description_inputs` handling from
        // interaction. In master, handle it in XML instead. It is currently
        // handled in JS to support already dropped snippets as well.
        dynamicContent = {
            ...this.dynamicContent,
            "#s_donation_description_inputs": {
                "t-att-class": () => ({ "d-none": false }),
            },
        };

        setup() {
            super.setup();
            const descInputsWrapperEl = this.el.querySelector(
                ":scope:not(.s_donation_inline) #s_donation_description_inputs"
            );
            if (
                descInputsWrapperEl &&
                descInputsWrapperEl !== descInputsWrapperEl.parentElement.firstElementChild
            ) {
                descInputsWrapperEl.parentElement.prepend(descInputsWrapperEl);
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
