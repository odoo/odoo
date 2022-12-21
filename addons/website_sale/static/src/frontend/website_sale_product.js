/** @odoo-module **/

import { registry, Widget } from "web.public.widget";
import { WebsiteSaleOptionsWithCartButton } from "./website_sale_options";

/**
 * Widget responsible the individual product pages.
 */
export const WebsiteSaleProduct = Widget.extend({
    selector: ".o_wsale_product_page",
    // Selector for 
    websiteSaleVariantSelector: ".js_product",

    start() {
        const result = this._super(...arguments);
        const optionsSelector = document.querySelector(this.websiteSaleVariantSelector);
        if (optionsSelector) {
            const optionSelectorWidget = new WebsiteSaleOptionsWithCartButton(this);
            optionSelectorWidget.attachTo(optionsSelector);
        }
        return result;
    }
});
registry.WebsiteSaleProduct = WebsiteSaleProduct;
