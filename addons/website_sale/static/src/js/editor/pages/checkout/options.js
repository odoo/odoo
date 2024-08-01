import { registerWebsiteOption } from "@website/js/editor/snippets.registry";

registerWebsiteOption("WebsiteSaleCheckoutPage", {
    template: "website_sale.checkout_page",
    selector: "main:has(.oe_website_sale .o_wizard)",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
        pageOptions: true,
    },
});
