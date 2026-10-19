import { DonationSnippet } from "./donation_snippet";
import { registry } from "@web/core/registry";

const DonationSnippetEdit = I => class extends I {
    submitDonation() { }
};

registry
    .category("public.interactions.edit")
    .add("website_sale.donation_snippet", {
        Interaction: DonationSnippet,
        mixin: DonationSnippetEdit,
    });
