import { registerWebsiteOption } from "@website/js/editor/snippets.registry";

registerWebsiteOption("HeaderShoppingCart", {
    template: "website_sale.HeaderShoppingCart",
    selector: "#wrapwrap > header",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
});
