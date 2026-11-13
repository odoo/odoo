import { registry } from "@web/core/registry";
import { BelowTopFixedElements } from "@website/interactions/below_top_fixed_elements";

export class WebsiteSaleStickyObject extends BelowTopFixedElements {
    static selector = ".o_wsale_sticky_object";
}

registry
    .category("public.interactions")
    .add("website.website_sale_product_sticky_col", WebsiteSaleStickyObject);

registry
    .category("public.interactions.edit")
    .add("website.website_sale_product_sticky_col", { Interaction: WebsiteSaleStickyObject });
