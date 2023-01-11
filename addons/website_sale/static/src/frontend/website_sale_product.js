/** @odoo-module **/

import { registry, Widget } from "web.public.widget";
import { animateClone, updateCartNavBar } from "./utils";
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
        on_product_added: "onProductAdded",
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

    // PRODUCT IMAGE
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

    // BUSINESS LOGIC
    async onProductAdded(ev) {
        if (this.getProductImageWidth() === "none") {
            return;
        }
        const data = ev.data.data;
        if (
            data.cart_quantity &&
            data.cart_quantity !== parseInt(document.querySelector(".my_cart_quantity")?.textContent)
        ) {
            await animateClone(
                $(document.querySelector("header .o_wsale_my_cart")),
                $(this.getProductImageContainer()),
                25,
                40
            );
            updateCartNavBar(data);
        }
    },
});
registry.WebsiteSaleProduct = WebsiteSaleProduct;
