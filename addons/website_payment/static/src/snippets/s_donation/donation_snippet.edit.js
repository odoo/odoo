import { DonationSnippet } from "./donation_snippet";
import { registry } from "@web/core/registry";

const DonationSnippetEdit = I => class extends I {
    onDonateClick() { }
};

registry
    .category("public.interactions.edit")
    .add("website_payment.donation_snippet", {
        Interaction: DonationSnippet,
        mixin: DonationSnippetEdit,
    });
