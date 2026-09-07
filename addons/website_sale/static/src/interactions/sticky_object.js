import { StickBelowHeader } from "@website/interactions/sticky_below_header";
import { registry } from "@web/core/registry";

export class WebsiteSaleStickyObject extends StickBelowHeader {
    static selector = ".o_wsale_sticky_object";
}

registry
    .category("public.interactions")
    .add("website.website_sale_product_sticky_col", WebsiteSaleStickyObject);

registry
    .category("public.interactions.edit")
    .add("website.website_sale_product_sticky_col", { Interaction: WebsiteSaleStickyObject });
