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
        const optionsSelector = this.el.querySelector(this.websiteSaleVariantSelector);
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
        this.getProductImageContainer().classList.toggle(
            "css_not_available",
            !ev.data.combinationData.is_combination_possible
        );
    },

    /**
     * Called by the option manager before fetching the combination info.
     */
    onRequestCombinationInfoParams(ev) {
        //TODO: is this necessary?
    },

    getProductImageLayout: function () {
        return this.el.querySelector("#product_detail_main").dataset.image_layout;
    },
    getProductImageWidth: function () {
        return this.el.querySelector("#product_detail_main").dataset.image_width;
    },
    getProductImageContainerSelector: function () {
        return {
            carousel: "#o-carousel-product",
            grid: "#o-grid-product",
        }[this.getProductImageLayout()];
    },
    getProductImageContainer: function () {
        return this.el.querySelector(this.getProductImageContainerSelector());
    },
});
registry.WebsiteSaleProduct = WebsiteSaleProduct;
