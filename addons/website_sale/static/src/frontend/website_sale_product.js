/** @odoo-module **/

import { registry, Widget } from "web.public.widget";
import { WebsiteSaleOptionsWithCartButton } from "./website_sale_options";

/**
 * Widget responsible the individual product pages.
 */
export const WebsiteSaleProduct = Widget.extend({
    selector: ".o_wsale_product_page",
    websiteSaleVariantSelector: ".js_product",
    custom_events: {
        combination_change: "onCombinationChange",
        get_combination_info_params: "onRequestCombinationInfoParams",
    },

    start() {
        const result = this._super(...arguments);
        const optionsSelector = document.querySelector(this.websiteSaleVariantSelector);
        if (optionsSelector) {
            const optionSelectorWidget = new WebsiteSaleOptionsWithCartButton(this);
            optionSelectorWidget.attachTo(optionsSelector);
        }
        return result;
    },

    /**
     * Called by the option manager when the combination has to be reloaded.
     */
    onCombinationChange(ev) {
        console.log("product page detected combination info change", ev.data.info);
    },

    /**
     * Called by the option manager before fetching the combination info.
     */
    onRequestCombinationInfoParams(ev) {
        //TODO: necessary?
    },
});
registry.WebsiteSaleProduct = WebsiteSaleProduct;
