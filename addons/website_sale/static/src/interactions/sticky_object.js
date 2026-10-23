import { registry } from "@web/core/registry";
import { StickyBelowHeader } from "@website/interactions/sticky_below_header";

export class WebsiteSaleStickyObject extends StickyBelowHeader {
    static selector = ".o_wsale_sticky_object";
}

registry
    .category("public.interactions")
    .add("website.website_sale_product_sticky_col", WebsiteSaleStickyObject);

registry
    .category("public.interactions.edit")
    .add("website.website_sale_product_sticky_col", { Interaction: WebsiteSaleStickyObject });
